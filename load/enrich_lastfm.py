
"""
enrich_lastfm.py

Enrich Spotify tracks or artists with public Last.fm metadata.

Writes only to:
    lastfm_track_metadata
    lastfm_artist_metadata
    external_track_tags
    external_artist_tags

Does not modify Spotify metadata, MusicBrainz results,
canonical song identities, or listening history.

Examples:
    python -m load.enrich_lastfm --entity tracks --limit 10
    python -m load.enrich_lastfm --entity artists --limit 10
    python -m load.enrich_lastfm --entity tracks --all
    python -m load.enrich_lastfm --entity artists --all
"""

import argparse
import os
import time
from datetime import datetime

import requests
from sqlalchemy import text

from load.database import engine


# ============================================================
# Configuration
# ============================================================

API_URL = "https://ws.audioscrobbler.com/2.0/"

REQUEST_INTERVAL_SECONDS = 0.5
MAX_RETRIES = 3
USER_AGENT = "SpotifyListeningAnalytics/1.0"


# ============================================================
# Helpers
# ============================================================

def as_int(value):
    """Convert an API value to an integer, or return None."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_text(value):
    """Return a non-empty string or None."""

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def normalize_list(value):
    """Normalize Last.fm's single-item or multi-item JSON lists."""

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return [value]

    return []


def extract_tags(container):
    """
    Extract Last.fm tags from either track or artist metadata.

    Expected structures:
        track.toptags.tag
        artist.tags.tag
    """

    if not isinstance(container, dict):
        return []

    if "toptags" in container:
        tags_container = container.get("toptags") or {}
    else:
        tags_container = container.get("tags") or {}

    if not isinstance(tags_container, dict):
        return []

    tags = normalize_list(tags_container.get("tag"))
    results = []
    seen = set()

    for position, tag in enumerate(tags, start=1):
        if not isinstance(tag, dict):
            continue

        name = as_text(tag.get("name"))

        if not name:
            continue

        key = name.casefold()

        if key in seen:
            continue

        seen.add(key)

        results.append({
            "name": name,
            "count": as_int(tag.get("count")),
            "position": position,
        })

    return results


def extract_wiki(container):
    """Extract summary and content from Last.fm wiki metadata."""

    wiki = container.get("wiki") or {}

    if not isinstance(wiki, dict):
        return None, None

    return (
        as_text(wiki.get("summary")),
        as_text(wiki.get("content")),
    )


def is_empty_result(metadata, tags, summary, content):
    """
    Detect Last.fm's low-information placeholder responses.

    Last.fm can return a track object for an item with no meaningful
    community data. Treat an entirely empty result as not_found.
    """

    has_mbid = bool(as_text(metadata.get("mbid")))
    listeners = as_int(metadata.get("listeners")) or 0
    playcount = as_int(metadata.get("playcount")) or 0

    return (
        not has_mbid
        and not tags
        and not summary
        and not content
        and listeners <= 2
        and playcount <= 4
    )


# ============================================================
# Last.fm API Client
# ============================================================

class LastFMClient:
    """Conservative, retrying client for the public Last.fm API."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
        })
        self.last_request_time = 0.0

    def get_info(self, method, artist, track=None):
        """Retrieve artist.getInfo or track.getInfo."""

        params = {
            "method": method,
            "api_key": self.api_key,
            "format": "json",
            "autocorrect": 1,
            "artist": artist,
        }

        if track is not None:
            params["track"] = track

        for attempt in range(MAX_RETRIES):
            elapsed = time.monotonic() - self.last_request_time

            if elapsed < REQUEST_INTERVAL_SECONDS:
                time.sleep(
                    REQUEST_INTERVAL_SECONDS - elapsed
                )

            try:
                response = self.session.get(
                    API_URL,
                    params=params,
                    timeout=30,
                )

                self.last_request_time = time.monotonic()

                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue

                response.raise_for_status()
                payload = response.json()

                # Last.fm can report API errors inside an HTTP 200.
                if "error" in payload:
                    error_code = payload.get("error")
                    error_message = payload.get(
                        "message",
                        "Unknown Last.fm API error",
                    )

                    if str(error_code) == "29":
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(2 ** (attempt + 2))
                            continue

                    raise RuntimeError(
                        f"Last.fm API error {error_code}: "
                        f"{error_message}"
                    )

                return payload

            except requests.RequestException:
                if attempt == MAX_RETRIES - 1:
                    raise

                time.sleep(2 ** (attempt + 1))

        raise RuntimeError(
            f"Last.fm request failed: {method}"
        )


# ============================================================
# Database: Track Queue
# ============================================================

def get_pending_tracks(limit=None):
    """Find Spotify tracks not yet processed by Last.fm."""

    limit_clause = "LIMIT :row_limit" if limit is not None else ""

    query = text(f"""
        SELECT
            tm.spotify_id,
            tm.track_name,
            tm.primary_artist_id,
            am.artist_name,
            mb.recording_mbid
        FROM track_metadata tm
        JOIN artist_metadata am
            ON am.artist_id = tm.primary_artist_id
        LEFT JOIN musicbrainz_track_metadata mb
            ON mb.spotify_id = tm.spotify_id
        LEFT JOIN lastfm_track_metadata lf
            ON lf.spotify_id = tm.spotify_id
        WHERE
            lf.spotify_id IS NULL
            OR lf.lookup_status IN ('pending', 'error')
        ORDER BY tm.spotify_id
        {limit_clause}
    """)

    params = {"row_limit": limit} if limit is not None else {}

    with engine.connect() as connection:
        result = connection.execute(query, params)
        return [dict(row) for row in result.mappings().all()]


# ============================================================
# Database: Artist Queue
# ============================================================

def get_pending_artists(limit=None):
    """Find Spotify artists not yet processed by Last.fm."""

    limit_clause = "LIMIT :row_limit" if limit is not None else ""

    query = text(f"""
        SELECT
            am.artist_id,
            am.artist_name
        FROM artist_metadata am
        LEFT JOIN lastfm_artist_metadata lf
            ON lf.spotify_artist_id = am.artist_id
        WHERE
            lf.spotify_artist_id IS NULL
            OR lf.lookup_status IN ('pending', 'error')
        ORDER BY am.artist_id
        {limit_clause}
    """)

    params = {"row_limit": limit} if limit is not None else {}

    with engine.connect() as connection:
        result = connection.execute(query, params)
        return [dict(row) for row in result.mappings().all()]


# ============================================================
# Database: Tag Replacement
# ============================================================

def replace_tags(table, id_column, spotify_id, tags):
    """
    Replace tags for one successfully processed entity.

    Table and column names are internal constants, never user input.
    """

    delete_query = text(f"""
        DELETE FROM {table}
        WHERE {id_column} = :entity_id
          AND source = 'lastfm'
    """)

    insert_query = text(f"""
        INSERT INTO {table} (
            {id_column},
            source,
            tag_name,
            tag_count,
            tag_position,
            retrieved_at
        )
        VALUES (
            :entity_id,
            'lastfm',
            :tag_name,
            :tag_count,
            :tag_position,
            :retrieved_at
        )
        ON DUPLICATE KEY UPDATE
            tag_count = VALUES(tag_count),
            tag_position = VALUES(tag_position),
            retrieved_at = VALUES(retrieved_at)
    """)

    now = datetime.now()

    with engine.begin() as connection:
        connection.execute(
            delete_query,
            {"entity_id": spotify_id},
        )

        for tag in tags:
            connection.execute(
                insert_query,
                {
                    "entity_id": spotify_id,
                    "tag_name": tag["name"],
                    "tag_count": tag["count"],
                    "tag_position": tag["position"],
                    "retrieved_at": now,
                },
            )


# ============================================================
# Database: Track Metadata
# ============================================================

def save_track(track, metadata, tags, status, message=None):
    """Save Last.fm track metadata and its tags."""

    summary, content = extract_wiki(metadata)

    record = {
        "spotify_id": track["spotify_id"],
        "lastfm_mbid": as_text(metadata.get("mbid")),
        "lastfm_track_url": as_text(metadata.get("url")),
        "listeners": as_int(metadata.get("listeners")),
        "playcount": as_int(metadata.get("playcount")),
        "summary": summary,
        "content": content,
        "lookup_status": status,
        "lookup_message": message,
        "raw_response": None,
        "last_checked_at": datetime.now(),
    }

    query = text("""
        INSERT INTO lastfm_track_metadata (
            spotify_id,
            lastfm_mbid,
            lastfm_track_url,
            listeners,
            playcount,
            summary,
            content,
            lookup_status,
            lookup_message,
            raw_response,
            last_checked_at
        )
        VALUES (
            :spotify_id,
            :lastfm_mbid,
            :lastfm_track_url,
            :listeners,
            :playcount,
            :summary,
            :content,
            :lookup_status,
            :lookup_message,
            :raw_response,
            :last_checked_at
        )
        ON DUPLICATE KEY UPDATE
            lastfm_mbid = VALUES(lastfm_mbid),
            lastfm_track_url = VALUES(lastfm_track_url),
            listeners = VALUES(listeners),
            playcount = VALUES(playcount),
            summary = VALUES(summary),
            content = VALUES(content),
            lookup_status = VALUES(lookup_status),
            lookup_message = VALUES(lookup_message),
            raw_response = VALUES(raw_response),
            last_checked_at = VALUES(last_checked_at)
    """)

    with engine.begin() as connection:
        connection.execute(query, record)

    replace_tags(
        table="external_track_tags",
        id_column="spotify_id",
        spotify_id=track["spotify_id"],
        tags=tags,
    )


# ============================================================
# Database: Artist Metadata
# ============================================================

def save_artist(artist, metadata, tags, status, message=None):
    """Save Last.fm artist metadata and its tags."""

    summary, content = extract_wiki(metadata)

    record = {
        "spotify_artist_id": artist["artist_id"],
        "lastfm_artist_name": as_text(metadata.get("name")),
        "lastfm_artist_url": as_text(metadata.get("url")),
        "lastfm_mbid": as_text(metadata.get("mbid")),
        "listeners": as_int(metadata.get("stats", {}).get("listeners")),
        "playcount": as_int(metadata.get("stats", {}).get("playcount")),
        "summary": summary,
        "content": content,
        "lookup_status": status,
        "lookup_message": message,
        "raw_response": None,
        "last_checked_at": datetime.now(),
    }

    query = text("""
        INSERT INTO lastfm_artist_metadata (
            spotify_artist_id,
            lastfm_artist_name,
            lastfm_artist_url,
            lastfm_mbid,
            listeners,
            playcount,
            summary,
            content,
            lookup_status,
            lookup_message,
            raw_response,
            last_checked_at
        )
        VALUES (
            :spotify_artist_id,
            :lastfm_artist_name,
            :lastfm_artist_url,
            :lastfm_mbid,
            :listeners,
            :playcount,
            :summary,
            :content,
            :lookup_status,
            :lookup_message,
            :raw_response,
            :last_checked_at
        )
        ON DUPLICATE KEY UPDATE
            lastfm_artist_name = VALUES(lastfm_artist_name),
            lastfm_artist_url = VALUES(lastfm_artist_url),
            lastfm_mbid = VALUES(lastfm_mbid),
            listeners = VALUES(listeners),
            playcount = VALUES(playcount),
            summary = VALUES(summary),
            content = VALUES(content),
            lookup_status = VALUES(lookup_status),
            lookup_message = VALUES(lookup_message),
            raw_response = VALUES(raw_response),
            last_checked_at = VALUES(last_checked_at)
    """)

    with engine.begin() as connection:
        connection.execute(query, record)

    replace_tags(
        table="external_artist_tags",
        id_column="spotify_artist_id",
        spotify_id=artist["artist_id"],
        tags=tags,
    )


# ============================================================
# Track Enrichment
# ============================================================

def enrich_tracks(client, tracks):
    totals = {
        "matched": 0,
        "not_found": 0,
        "error": 0,
    }

    for index, track in enumerate(tracks, start=1):
        print(
            f"[{index}/{len(tracks)}] "
            f"{track['track_name']} by {track['artist_name']}"
        )

        try:
            payload = client.get_info(
                method="track.getInfo",
                artist=track["artist_name"],
                track=track["track_name"],
            )

            metadata = payload.get("track")

            if not isinstance(metadata, dict):
                save_track(
                    track, {}, [], "not_found",
                    "Last.fm returned no track object.",
                )
                totals["not_found"] += 1
                print("    Status: not_found")
                continue

            tags = extract_tags(metadata)
            summary, content = extract_wiki(metadata)

            status = (
                "not_found"
                if is_empty_result(
                    metadata, tags, summary, content
                )
                else "matched"
            )

            save_track(
                track,
                metadata,
                tags,
                status,
                (
                    "Last.fm returned no meaningful metadata."
                    if status == "not_found"
                    else None
                ),
            )

            totals[status] += 1
            print(
                f"    Status: {status} | "
                f"Tags: {len(tags)}"
            )

        except Exception as error:
            message = str(error)[:1000]
            print(f"    Lookup error: {message}")

            save_track(
                track, {}, [], "error", message
            )
            totals["error"] += 1

    return totals


# ============================================================
# Artist Enrichment
# ============================================================

def enrich_artists(client, artists):
    totals = {
        "matched": 0,
        "not_found": 0,
        "error": 0,
    }

    for index, artist in enumerate(artists, start=1):
        print(
            f"[{index}/{len(artists)}] "
            f"{artist['artist_name']}"
        )

        try:
            payload = client.get_info(
                method="artist.getInfo",
                artist=artist["artist_name"],
            )

            metadata = payload.get("artist")

            if not isinstance(metadata, dict):
                save_artist(
                    artist, {}, [], "not_found",
                    "Last.fm returned no artist object.",
                )
                totals["not_found"] += 1
                print("    Status: not_found")
                continue

            tags = extract_tags(metadata)
            summary, content = extract_wiki(metadata)

            status = (
                "not_found"
                if is_empty_result(
                    {
                        "mbid": metadata.get("mbid"),
                        "listeners": (
                            metadata.get("stats") or {}
                        ).get("listeners"),
                        "playcount": (
                            metadata.get("stats") or {}
                        ).get("playcount"),
                    },
                    tags,
                    summary,
                    content,
                )
                else "matched"
            )

            save_artist(
                artist,
                metadata,
                tags,
                status,
                (
                    "Last.fm returned no meaningful metadata."
                    if status == "not_found"
                    else None
                ),
            )

            totals[status] += 1
            print(
                f"    Status: {status} | "
                f"Tags: {len(tags)}"
            )

        except Exception as error:
            message = str(error)[:1000]
            print(f"    Lookup error: {message}")

            save_artist(
                artist, {}, [], "error", message
            )
            totals["error"] += 1

    return totals


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Enrich Spotify metadata using Last.fm."
    )

    parser.add_argument(
        "--entity",
        choices=["tracks", "artists"],
        default="tracks",
        help="Which type of metadata to enrich (default: tracks).",
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum records to process (default: 10).",
    )

    group.add_argument(
        "--all",
        action="store_true",
        help="Process all eligible records for the chosen entity.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1.")

    api_key = os.getenv("LASTFM_API_KEY")

    if not api_key:
        parser.error(
            "LASTFM_API_KEY is missing. Add it to your project .env file."
        )

    limit = None if args.all else (
        args.limit if args.limit is not None else 10
    )

    if args.entity == "tracks":
        records = get_pending_tracks(limit)
    else:
        records = get_pending_artists(limit)

    print(f"Entity: {args.entity}")
    print(f"Records queued: {len(records):,}")

    if not records:
        print("No eligible records found.")
        return

    client = LastFMClient(api_key)

    if args.entity == "tracks":
        totals = enrich_tracks(client, records)
    else:
        totals = enrich_artists(client, records)

    print("\n=== LAST.FM ENRICHMENT SUMMARY ===")

    for status, count in totals.items():
        print(f"{status}: {count:,}")

    print("\nLast.fm enrichment finished.")
    print("Existing Spotify and MusicBrainz tables were not changed.")


if __name__ == "__main__":
    main()
