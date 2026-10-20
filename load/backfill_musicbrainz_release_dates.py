
"""
backfill_musicbrainz_release_dates.py

Retrieve missing release dates for already-matched MusicBrainz
recordings.

This script updates only:
    - first_release_date
    - first_release_date_precision
    - release_mbids, when new release IDs are available
    - lookup_message, when no release date is found

It does not change Spotify metadata, matching decisions,
recording IDs, or the listening-history warehouse.

Usage:
    python -m load.backfill_musicbrainz_release_dates
    python -m load.backfill_musicbrainz_release_dates --limit 10
"""

import argparse
import json
from datetime import datetime

from sqlalchemy import text

from load.database import engine
from load.enrich_musicbrainz_tracks import (
    MusicBrainzClient,
    get_release_information,
)


# ============================================================
# Database Queries
# ============================================================

def get_recordings_needing_dates(limit):
    """Find matched recordings that have no recorded release date."""

    query = text("""
        SELECT
            spotify_id,
            recording_mbid,
            recording_title
        FROM musicbrainz_track_metadata
        WHERE
            lookup_status = 'matched'
            AND recording_mbid IS NOT NULL
            AND first_release_date IS NULL
            AND (
                lookup_message IS NULL
                OR lookup_message NOT LIKE
                    'Release-date backfill checked:%'
            )
        ORDER BY spotify_id
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


def save_release_information(
    spotify_id,
    release_ids,
    release_date,
    date_precision,
):
    """
    Update release information without replacing good values
    with NULL or changing the existing match.
    """

    query = text("""
        UPDATE musicbrainz_track_metadata
        SET
            first_release_date = COALESCE(
                first_release_date,
                :release_date
            ),
            first_release_date_precision = COALESCE(
                first_release_date_precision,
                :date_precision
            ),
            release_mbids = CASE
                WHEN JSON_LENGTH(:release_mbids) > 0
                THEN :release_mbids
                ELSE release_mbids
            END,
            lookup_message = CASE
                WHEN :release_date IS NULL
                THEN :no_date_message
                ELSE lookup_message
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE
            spotify_id = :spotify_id
            AND lookup_status = 'matched'
            AND recording_mbid IS NOT NULL
            AND first_release_date IS NULL
    """)

    release_json = json.dumps(release_ids)

    params = {
        "spotify_id": spotify_id,
        "release_date": release_date,
        "date_precision": date_precision,
        "release_mbids": release_json,
        "no_date_message": (
            "Release-date backfill checked: "
            "MusicBrainz returned no release date."
        ),
    }

    with engine.begin() as connection:
        result = connection.execute(query, params)

    return result.rowcount


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Backfill missing MusicBrainz release dates "
            "for previously matched recordings."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum recordings to process (default: 25).",
    )

    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1.")

    recordings = get_recordings_needing_dates(args.limit)

    print(
        f"Matched recordings missing release dates: "
        f"{len(recordings):,}"
    )

    if not recordings:
        print("No recordings need a release-date backfill.")
        return

    client = MusicBrainzClient()

    totals = {
        "dates_added": 0,
        "no_date_available": 0,
        "errors": 0,
    }

    for index, item in enumerate(recordings, start=1):
        spotify_id = item["spotify_id"]
        recording_mbid = item["recording_mbid"]

        print(
            f"[{index}/{len(recordings)}] "
            f"{item['recording_title']} "
            f"({recording_mbid})"
        )

        try:
            response = client.lookup_recording(
                recording_mbid
            )

            release_ids, release_date, precision = (
                get_release_information(response)
            )

            if release_date:
                updated = save_release_information(
                    spotify_id=spotify_id,
                    release_ids=release_ids,
                    release_date=release_date,
                    date_precision=precision,
                )

                if updated:
                    totals["dates_added"] += 1
                    print(
                        f"    Release date: {release_date} "
                        f"({precision})"
                    )
                else:
                    print(
                        "    No update needed; the row may "
                        "already have a release date."
                    )

            else:
                save_release_information(
                    spotify_id=spotify_id,
                    release_ids=release_ids,
                    release_date=None,
                    date_precision=None,
                )

                totals["no_date_available"] += 1
                print("    No release date returned.")

        except Exception as error:
            totals["errors"] += 1
            print(f"    Lookup error: {error}")

    print("\n=== RELEASE-DATE BACKFILL SUMMARY ===")
    print(f"Dates added: {totals['dates_added']:,}")
    print(
        "No date available: "
        f"{totals['no_date_available']:,}"
    )
    print(f"Errors: {totals['errors']:,}")
    print("\nBackfill finished. Existing matches were preserved.")


if __name__ == "__main__":
    main()
