
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


def normalize_title(value):
    """Normalize titles while removing common version annotations."""

    value = normalize(value)

    # Remove common featured-artist annotations from the normalized
    # title. The featured artists are evaluated separately.
    return value


def duration_similarity(spotify_duration_ms, mb_duration_ms):
    """Return a duration agreement score from 0 to 1."""

    if not spotify_duration_ms or not mb_duration_ms:
        return None

    difference_ms = abs(
        int(spotify_duration_ms) - int(mb_duration_ms)
    )

    # Recordings within two seconds receive full duration credit.
    if difference_ms <= 2000:
        return 1.0

    # Penalize differences beyond two seconds gradually.
    return max(0.0, 1.0 - difference_ms / 15000)


def score_recording(
    recording,
    track_name,
    artist_name,
    spotify_artist_names=None,
    spotify_duration_ms=None,
):
    """
    Score a MusicBrainz recording against Spotify title, artist credits,
    and duration.
    """

    title_score = similarity(
        track_name,
        recording.get("title"),
    )

    mb_artist_names = get_credit_names(
        recording.get("artist-credit")
    )

    spotify_artist_names = spotify_artist_names or []

    # Ensure the primary Spotify artist is included.
    if artist_name and artist_name not in spotify_artist_names:
        spotify_artist_names.append(artist_name)

    artist_scores = [
        similarity(spotify_artist, mb_artist)
        for spotify_artist in spotify_artist_names
        for mb_artist in mb_artist_names
    ]

    artist_score = max(artist_scores, default=0.0)

    # Reward coverage of multiple credited Spotify artists when
    # MusicBrainz also credits them.
    matched_artist_count = sum(
        1
        for spotify_artist in spotify_artist_names
        if any(
            similarity(spotify_artist, mb_artist) >= 0.85
            for mb_artist in mb_artist_names
        )
    )

    if spotify_artist_names:
        artist_coverage = (
            matched_artist_count / len(spotify_artist_names)
        )
    else:
        artist_coverage = 0.0

    mb_duration_ms = recording.get("length")
    duration_score = duration_similarity(
        spotify_duration_ms,
        mb_duration_ms,
    )

    # Weight title and artist agreement most heavily. Duration
    # helps distinguish alternate recordings when available.
    if duration_score is None:
        combined_score = (
            0.60 * title_score
            + 0.30 * artist_score
            + 0.10 * artist_coverage
        )
    else:
        combined_score = (
            0.50 * title_score
            + 0.25 * artist_score
            + 0.10 * artist_coverage
            + 0.15 * duration_score
        )

    return {
        "recording": recording,
        "title_score": title_score,
        "artist_score": artist_score,
        "artist_coverage": artist_coverage,
        "duration_score": duration_score,
        "combined_score": combined_score,
    }


def choose_recording(
    recordings,
    track_name,
    artist_name,
    spotify_artist_names=None,
    spotify_duration_ms=None,
):
    """
    Choose a recording only when evidence supports a reliable match.

    Identical duplicate candidates can be resolved when their scores
    and metadata agree. Different versions remain ambiguous when
    the available evidence cannot distinguish them.
    """

    if not recordings:
        return None, "not_found", None

    scored = [
        score_recording(
            recording=recording,
            track_name=track_name,
            artist_name=artist_name,
            spotify_artist_names=spotify_artist_names,
            spotify_duration_ms=spotify_duration_ms,
        )
        for recording in recordings
    ]

    scored.sort(
        key=lambda item: item["combined_score"],
        reverse=True,
    )

    best = scored[0]

    # Minimum evidence requirements.
    if (
        best["title_score"] < 0.80
        or best["artist_score"] < 0.80
        or best["combined_score"] < 0.80
    ):
        return None, "ambiguous", best["combined_score"]

    if len(scored) == 1:
        return (
            best["recording"],
            "matched",
            best["combined_score"],
        )

    second = scored[1]

    score_gap = (
        best["combined_score"]
        - second["combined_score"]
    )

    # If the leading candidate is clearly better, accept it.
    if score_gap >= 0.08:
        return (
            best["recording"],
            "matched",
            best["combined_score"],
        )

    # If multiple candidates tie, accept only when their title,
    # artist credits, and durations are equivalent enough that
    # the duplicate entries do not change the likely recording.
    best_recording = best["recording"]
    second_recording = second["recording"]

    same_title = (
        normalize(best_recording.get("title"))
        == normalize(second_recording.get("title"))
    )

    best_artists = sorted(
        normalize(name)
        for name in get_credit_names(
            best_recording.get("artist-credit")
        )
    )

    second_artists = sorted(
        normalize(name)
        for name in get_credit_names(
            second_recording.get("artist-credit")
        )
    )

    same_artists = best_artists == second_artists

    best_length = best_recording.get("length")
    second_length = second_recording.get("length")

    durations_compatible = (
        best_length is None
        or second_length is None
        or abs(best_length - second_length) <= 2000
    )

    if (
        same_title
        and same_artists
        and durations_compatible
        and best["combined_score"] >= 0.90
    ):
        return (
            best_recording,
            "matched",
            best["combined_score"],
        )

    return None, "ambiguous", best["combined_score"]


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
            tm.duration_ms,
            am.artist_name,
            (
                SELECT JSON_ARRAYAGG(am2.artist_name)
                FROM track_artists ta
                JOIN artist_metadata am2
                    ON am2.artist_id = ta.artist_id
                WHERE ta.spotify_id = tm.spotify_id
            ) AS artist_names_json
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
        ORDER BY tm.spotify_id
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
            
            artist_names = track.get("artist_names_json")

            if isinstance(artist_names, str):
                try:
                    artist_names = json.loads(artist_names)
                except json.JSONDecodeError:
                    artist_names = []

            recording, status, score = choose_recording(
                recordings=response_data.get("recordings", []),
                track_name=track["track_name"],
                artist_name=track["artist_name"],
                spotify_artist_names=artist_names or [],
                spotify_duration_ms=track["duration_ms"],
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
