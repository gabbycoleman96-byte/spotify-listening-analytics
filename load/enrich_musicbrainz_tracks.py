
"""
enrich_musicbrainz_tracks.py

Enrich Spotify tracks with MusicBrainz recording metadata.

This script is intentionally separate from the main ETL pipeline.
It reads existing Spotify metadata and writes only to
musicbrainz_track_metadata.

Usage:
    python -m load.enrich_musicbrainz_tracks
    python -m load.enrich_musicbrainz_tracks --limit 10
"""

import argparse
import json
import re
import time
from datetime import datetime
from difflib import SequenceMatcher

import requests
from sqlalchemy import text

from load.database import engine


# ============================================================
# Configuration
# ============================================================

API_BASE = "https://musicbrainz.org/ws/2"
USER_AGENT = (
    "SpotifyListeningAnalytics/1.0 "
    "(https://github.com/gabbycoleman96-byte/"
    "spotify-listening-analytics)"
)

REQUEST_INTERVAL_SECONDS = 1.1
MAX_RETRIES = 3


# ============================================================
# Normalization and Matching
# ============================================================

def normalize(value):
    """Normalize text for conservative title/artist comparisons."""

    if not value:
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).casefold(),
    )


def similarity(first, second):
    """Return a text similarity score from 0 to 1."""

    first = normalize(first)
    second = normalize(second)

    if not first or not second:
        return 0.0

    return SequenceMatcher(
        None,
        first,
        second,
    ).ratio()


def get_credit_names(artist_credit):
    """Extract credited artist names from a MusicBrainz response."""

    names = []

    for credit in artist_credit or []:
        if not isinstance(credit, dict):
            continue

        artist = credit.get("artist") or {}

        name = (
            credit.get("name")
            or artist.get("name")
        )

        if name:
            names.append(name)

    return names


def score_recording(recording, track_name, artist_name):
    """
    Score a recording against Spotify title and primary artist.

    Title agreement receives slightly more weight, but both
    fields must meet minimum thresholds before accepting a match.
    """

    title_score = similarity(
        track_name,
        recording.get("title"),
    )

    credit_names = get_credit_names(
        recording.get("artist-credit")
    )

    artist_score = max(
        (
            similarity(artist_name, credit_name)
            for credit_name in credit_names
        ),
        default=0.0,
    )

    combined_score = (
        0.65 * title_score
        + 0.35 * artist_score
    )

    return {
        "recording": recording,
        "title_score": title_score,
        "artist_score": artist_score,
        "combined_score": combined_score,
    }


def choose_recording(recordings, track_name, artist_name):
    """
    Choose a recording only when the match is sufficiently clear.

    Returns:
        (candidate, status, score)

    A strong ISRC match alone is not enough if its results include
    recordings with different titles or artists.
    """

    if not recordings:
        return None, "not_found", None

    scored = [
        score_recording(
            recording,
            track_name,
            artist_name,
        )
        for recording in recordings
    ]

    scored.sort(
        key=lambda item: item["combined_score"],
        reverse=True,
    )

    best = scored[0]

    if (
        best["title_score"] < 0.85
        or best["artist_score"] < 0.65
        or best["combined_score"] < 0.80
    ):
        return None, "ambiguous", best["combined_score"]

    if len(scored) > 1:
        second = scored[1]

        if (
            best["combined_score"]
            - second["combined_score"]
            < 0.08
        ):
            return None, "ambiguous", best["combined_score"]

    return (
        best["recording"],
        "matched",
        best["combined_score"],
    )


# ============================================================
# Database Queries
# ============================================================

def get_pending_tracks(limit):
    """Find ISRC-bearing tracks without a completed lookup."""

    query = text("""
        SELECT
            tm.spotify_id,
            tm.track_name,
            tm.primary_artist_id,
            tm.isrc,
            am.artist_name
        FROM track_metadata tm
        LEFT JOIN artist_metadata am
            ON am.artist_id = tm.primary_artist_id
        LEFT JOIN musicbrainz_track_metadata mb
            ON mb.spotify_id = tm.spotify_id
        WHERE
            tm.isrc IS NOT NULL
            AND TRIM(tm.isrc) <> ''
            AND (
                mb.spotify_id IS NULL
                OR mb.lookup_status IN ('pending', 'error')
            )
        ORDER BY
            tm.spotify_id
        LIMIT :row_limit
    """)

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {"row_limit": limit},
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ============================================================
# MusicBrainz API
# ============================================================

class MusicBrainzClient:
    """Rate-limited MusicBrainz API client."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })
        self.last_request_time = 0.0

    def lookup_isrc(self, isrc):
        """Look up recordings associated with an ISRC."""

        url = f"{API_BASE}/isrc/{isrc}"

        for attempt in range(MAX_RETRIES):
            elapsed = time.monotonic() - self.last_request_time

            if elapsed < REQUEST_INTERVAL_SECONDS:
                time.sleep(
                    REQUEST_INTERVAL_SECONDS - elapsed
                )

            try:
                response = self.session.get(
                    url,
                    params={
                        "fmt": "json",
                        "inc": "artist-credits+releases",
                    },
                    timeout=30,
                )

                self.last_request_time = time.monotonic()

                if response.status_code in (429, 503):
                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    try:
                        wait_seconds = float(retry_after)
                    except (TypeError, ValueError):
                        wait_seconds = 2 ** (attempt + 1)

                    if attempt < MAX_RETRIES - 1:
                        time.sleep(
                            max(wait_seconds, 2 ** (attempt + 1))
                        )
                        continue

                if response.status_code == 404:
                    return {"recordings": []}
                
                response.raise_for_status()
                return response.json()

            except requests.RequestException:
                if attempt == MAX_RETRIES - 1:
                    raise

                time.sleep(2 ** (attempt + 1))

        raise RuntimeError(
            f"MusicBrainz lookup failed after retries: {isrc}"
        )

    
    def lookup_recording(self, recording_mbid):
        """Fetch a recording and its associated release information."""

        url = f"{API_BASE}/recording/{recording_mbid}"

        for attempt in range(MAX_RETRIES):
            elapsed = time.monotonic() - self.last_request_time

            if elapsed < REQUEST_INTERVAL_SECONDS:
                time.sleep(REQUEST_INTERVAL_SECONDS - elapsed)

            try:
                response = self.session.get(
                    url,
                    params={
                        "fmt": "json",
                        "inc": "artist-credits+releases",
                    },
                    timeout=30,
                )

                self.last_request_time = time.monotonic()

                if response.status_code in (429, 503):
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException:
                if attempt == MAX_RETRIES - 1:
                    raise

                time.sleep(2 ** (attempt + 1))

        raise RuntimeError(
            f"Recording lookup failed: {recording_mbid}"
        )


# ============================================================
# Recording Metadata
# ============================================================


def get_release_information(recording):
    """Extract release IDs and the earliest available release date."""

    releases = (
        recording.get("releases")
        or recording.get("release-list")
        or []
    )

    release_ids = [
        release["id"]
        for release in releases
        if release.get("id")
    ]

    dates = [
        release.get("date")
        for release in releases
        if release.get("date")
    ]

    # MusicBrainz recording responses may supply this directly.
    direct_date = (
        recording.get("first-release-date")
        or recording.get("first_release_date")
    )

    if direct_date:
        first_release_date = direct_date
    elif dates:
        first_release_date = min(dates)
    else:
        first_release_date = None

    if first_release_date:
        if len(first_release_date) == 4:
            precision = "year"
        elif len(first_release_date) == 7:
            precision = "month"
        else:
            precision = "day"
    else:
        precision = None

    return (
        release_ids,
        first_release_date,
        precision,
    )


def build_metadata_record(
    track,
    recording,
    status,
    score,
    raw_response,
    message=None,
):
    """Build a record matching the cache table schema."""

    now = datetime.now()

    if recording:
        (
            release_ids,
            first_release_date,
            date_precision,
        ) = get_release_information(recording)

        artist_credit = recording.get("artist-credit")

        length_ms = recording.get("length")

        if not isinstance(length_ms, int):
            length_ms = None

        return {
            "spotify_id": track["spotify_id"],
            "recording_mbid": recording.get("id"),
            "recording_title": recording.get("title"),
            "recording_length_ms": length_ms,
            "disambiguation": recording.get("disambiguation"),
            "first_release_date": first_release_date,
            "first_release_date_precision": date_precision,
            "artist_credit": json.dumps(artist_credit)
                if artist_credit is not None else None,
            "release_mbids": json.dumps(release_ids),
            "match_method": "isrc_title_artist",
            "match_score": score,
            "lookup_status": status,
            "lookup_message": message,
            "raw_response": json.dumps(raw_response),
            "last_checked_at": now,
        }

    return {
        "spotify_id": track["spotify_id"],
        "recording_mbid": None,
        "recording_title": None,
        "recording_length_ms": None,
        "disambiguation": None,
        "first_release_date": None,
        "first_release_date_precision": None,
        "artist_credit": None,
        "release_mbids": None,
        "match_method": "isrc",
        "match_score": score,
        "lookup_status": status,
        "lookup_message": message,
        "raw_response": json.dumps(raw_response),
        "last_checked_at": now,
    }


# ============================================================
# Database Upsert
# ============================================================

UPSERT_QUERY = text("""
    INSERT INTO musicbrainz_track_metadata (
        spotify_id,
        recording_mbid,
        recording_title,
        recording_length_ms,
        disambiguation,
        first_release_date,
        first_release_date_precision,
        artist_credit,
        release_mbids,
        match_method,
        match_score,
        lookup_status,
        lookup_message,
        raw_response,
        last_checked_at
    )
    VALUES (
        :spotify_id,
        :recording_mbid,
        :recording_title,
        :recording_length_ms,
        :disambiguation,
        :first_release_date,
        :first_release_date_precision,
        :artist_credit,
        :release_mbids,
        :match_method,
        :match_score,
        :lookup_status,
        :lookup_message,
        :raw_response,
        :last_checked_at
    )
    ON DUPLICATE KEY UPDATE
        recording_mbid = VALUES(recording_mbid),
        recording_title = VALUES(recording_title),
        recording_length_ms = VALUES(recording_length_ms),
        disambiguation = VALUES(disambiguation),
        first_release_date = VALUES(first_release_date),
        first_release_date_precision =
            VALUES(first_release_date_precision),
        artist_credit = VALUES(artist_credit),
        release_mbids = VALUES(release_mbids),
        match_method = VALUES(match_method),
        match_score = VALUES(match_score),
        lookup_status = VALUES(lookup_status),
        lookup_message = VALUES(lookup_message),
        raw_response = VALUES(raw_response),
        last_checked_at = VALUES(last_checked_at)
""")


def save_metadata(record):
    """Save one lookup result to the external metadata cache."""

    with engine.begin() as connection:
        connection.execute(
            UPSERT_QUERY,
            record,
        )


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Enrich Spotify tracks using MusicBrainz ISRCs."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum tracks to process in this run (default: 25).",
    )

    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1.")

    tracks = get_pending_tracks(args.limit)

    print(f"Tracks queued: {len(tracks):,}")

    if not tracks:
        print("No pending ISRC lookups found.")
        return

    client = MusicBrainzClient()

    totals = {
        "matched": 0,
        "not_found": 0,
        "ambiguous": 0,
        "error": 0,
    }

    for index, track in enumerate(tracks, start=1):
        spotify_id = track["spotify_id"]
        isrc = str(track["isrc"]).strip().upper()

        print(
            f"[{index}/{len(tracks)}] "
            f"{track['track_name']} "
            f"by {track['artist_name'] or 'Unknown artist'}"
        )

        try:
            response_data = client.lookup_isrc(isrc)

            recording, status, score = choose_recording(
                response_data.get("recordings", []),
                track["track_name"],
                track["artist_name"],
            )

            record = build_metadata_record(
                track=track,
                recording=recording,
                status=status,
                score=score,
                raw_response=response_data,
            )

            save_metadata(record)
            totals[status] += 1

            print(
                f"    Status: {status}"
                + (
                    f" | Score: {score:.3f}"
                    if score is not None
                    else ""
                )
            )

        except Exception as error:
            print(f"    Lookup error: {error}")

            error_record = build_metadata_record(
                track=track,
                recording=None,
                status="error",
                score=None,
                raw_response={},
                message=str(error)[:1000],
            )

            save_metadata(error_record)
            totals["error"] += 1

    print("\n=== MUSICBRAINZ LOOKUP SUMMARY ===")

    for status, count in totals.items():
        print(f"{status}: {count:,}")

    print("\nExternal metadata cache updated.")
    print("No existing Spotify or warehouse tables were changed.")


if __name__ == "__main__":
    main()
