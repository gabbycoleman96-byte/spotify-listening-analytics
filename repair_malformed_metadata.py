
"""
repair_malformed_metadata.py

Repairs a small, explicitly approved batch of malformed track metadata.

Original Spotify IDs, listening history, and canonical identity mappings
are preserved. Run with --apply to write changes after reviewing the
dry-run output.
"""

import argparse
import time
from datetime import UTC, datetime

from api.spotify_client import sp
from load.loader import execute_sql, fetch_dataframe, load_dataframe

from sqlalchemy import text

from load.database import engine


# Original Spotify ID -> verified candidate metadata source ID.

REPAIR_MAP = {
    "7BX9pdIbf4LkCIWmFYp3tN": {
        "candidate_id": "1Cdvrq9EdMb6QwSJwPpGSd",
        "track_name": "Celtic Cowboy",
        "artist_name": "Charlotte Funke",
    },
    "0CQskMydQ8AhtKhJUAolvE": {
        "candidate_id": "0NFc4BKlTsiDv3M8Gf4p61",
        "track_name": "Tallis One",
        "artist_name": "Samuel Lindon",
    },
    "5jxBweBbPFg53Ozudm6HrC": {
        "candidate_id": "0EhLVfXZ78vLPkSrE5rqZx",
        "track_name": "Faded Dreams",
        "artist_name": "Aaron Lansing",
    },
    "01T3AjynqSMVfiAQCAfrKJ": {
        "candidate_id": "77jHPKK4FnCrPvpH9bfN25",
        "track_name": "Evolutionistically Yours",
        "artist_name": "Józef Gatysik",
    },
    "1e3JUGxqyfe94XBFnWdP11": {
        "candidate_id": "0bFqBfmSPvqlCZ02bbh7eR",
        "track_name": "Talisman Stallion",
        "artist_name": "Bela Nemeth",
    },
    "2erBrCFQNgGeMKVta0XVcJ": {
        "candidate_id": "2o892JWoJ8mBJgCERI8iSQ",
        "track_name": "Crossing Over",
        "artist_name": "Les Clouds",
    },
    "1BkATl6u7ttnmZi6Y3vfcQ": {
        "candidate_id": "6EmWPtyzuo0YhX4U1AZGI8",
        "track_name": "La Valse D'Amélie",
        "artist_name": "Regina Mira",
    },
    "4KDVmpe3jP6ESQCmdclGUC": {
        "candidate_id": "1YwZE7e4AOwuRCHZhDKXW0",
        "track_name": "Old House On The Hill",
        "artist_name": "Les Clouds",
    },
    "504NLPDUBRylbZUUQR97XX": {
        "candidate_id": "0EhatQewc9cM0D6RS4aFPV",
        "track_name": "The Watchtower",
        "artist_name": "Sigimund",
    },
    "54MQc7UtIAogdoU5h0KNOP": {
        "candidate_id": "0dSRypFUcx91S2dyp24pBz",
        "track_name": "Twinkling Star",
        "artist_name": "Clark Ingram",
    },
    "5C0pEMNp1Qr4LNDI3T7eVF": {
        "candidate_id": "4WCts5QQmuYG6wxtNk9BRX",
        "track_name": "Far and Beyond",
        "artist_name": "Charles Bolt",
    },
    "6gp6sejiJXYU1i6xHPf8hh": {
        "candidate_id": "1gqHiFzVd2dPCXfuP53DgQ",
        "track_name": "This Moment",
        "artist_name": "Bela Nemeth",
    },
    "7adF8nbrf6PWrdK7RPVjyF": {
        "candidate_id": "611uLQ9Fv4WpBxtv8v5Bo5",
        "track_name": "As Time Goes By",
        "artist_name": "Isabella Ivanova",
    },
    "2wBb2lAmkZZIioQcJpH8D6": {
        "candidate_id": "6tJkVhNGGK5nE4kHed36aR",
        "track_name": "As She Rises",
        "artist_name": "Dimitri Stöckl",
    },
    "5JJdBQbd2nokSTbDKk0dZm": {
        "candidate_id": "6pvQle5UPIiZtJZWyI7NHI",
        "track_name": "The Message",
        "artist_name": "Les Clouds",
    },
    "5uuVGnkZEFHBz8unViC3iA": {
        "candidate_id": "3X1oSEYbPipzoAGp6oDNhC",
        "track_name": "G-Shit (feat. Blockboi Twitch)",
        "artist_name": "Sidhu Moose Wala",
    },
    "6fhfMxO6LDmCKb0EsjYG0U": {
        "candidate_id": "7qmA1rkHMclCwjmUczWXD1",
        "track_name": "Smile",
        "artist_name": "Leigh Watershed",
    },
    "6GiPDAnfhmpqwTE8lRazQS": {
        "candidate_id": "2x1gaXZvBEMxAofYjw5nyT",
        "track_name": "Moon River",
        "artist_name": "Lucina Chase",
    },
    "7tfAVm2Fam6FpCkYhfcngh": {
        "candidate_id": "4AAb7TCeYOzDOpTSLcev7u",
        "track_name": "Swing Low Sweet Chariot",
        "artist_name": "Ofelia Marsh",
    },
}


def normalize(value):
    return " ".join(str(value or "").casefold().split())


def get_original_record(original_id):
    query = """
        SELECT
            tm.spotify_id,
            tm.track_name,
            tm.duration_ms,
            tm.album_id,
            tm.primary_artist_id,
            am.album_name
        FROM track_metadata AS tm
        LEFT JOIN album_metadata AS am
            ON am.album_id = tm.album_id
        WHERE tm.spotify_id = :spotify_id
    """

    df = fetch_dataframe(query.replace(
        "WHERE tm.spotify_id = :spotify_id",
        f"WHERE tm.spotify_id = '{original_id}'"
    ))

    if df.empty:
        raise ValueError(f"Original ID not found: {original_id}")

    return df.iloc[0]


def validate_candidate(original_id, config):
    candidate_id = config["candidate_id"]
    track = sp.track(candidate_id)

    if track.get("id") != candidate_id:
        raise ValueError(
            f"{config['track_name']}: Spotify returned an unexpected ID."
        )

    if normalize(track.get("name")) != normalize(config["track_name"]):
        raise ValueError(
            f"{config['track_name']}: candidate title did not match."
        )

    artists = track.get("artists", [])
    if not artists:
        raise ValueError(
            f"{config['track_name']}: candidate has no artists."
        )

    if normalize(artists[0].get("name")) != normalize(config["artist_name"]):
        raise ValueError(
            f"{config['track_name']}: primary artist did not match."
        )

    album = track.get("album") or {}
    duration_ms = track.get("duration_ms")

    if not album.get("id") or not album.get("name"):
        raise ValueError(
            f"{config['track_name']}: candidate album metadata is incomplete."
        )

    if not isinstance(duration_ms, int) or duration_ms <= 0:
        raise ValueError(
            f"{config['track_name']}: candidate duration is invalid."
        )

    original = get_original_record(original_id)

    if (
        str(original["track_name"] or "").strip()
        or int(original["duration_ms"] or 0) != 0
        or str(original["album_name"] or "").strip()
    ):
        raise ValueError(
            f"{config['track_name']}: original row no longer matches "
            "the expected malformed state. No change made."
        )

    return track




def repair_track(original_id, config, track, apply_changes):
    """Repair one malformed track without changing its identity."""
    album = track["album"]
    scraped_at = datetime.now(UTC)

    print(
        f"{config['track_name']} | "
        f"{config['artist_name']} | "
        f"{track['duration_ms']} ms | "
        f"Album: {album['name']}"
    )

    if not apply_changes:
        return

    images = album.get("images", [])
    album_image_url = None

    if images:
        largest_image = max(
            images,
            key=lambda image: image.get("height") or 0,
        )
        album_image_url = largest_image.get("url")

    album_params = {
        "album_id": album["id"],
        "album_uri": album.get("uri"),
        "album_name": album.get("name"),
        "album_type": album.get("album_type"),
        "release_date": album.get("release_date"),
        "release_date_precision": album.get("release_date_precision"),
        "total_tracks": album.get("total_tracks"),
        "album_art_url": album_image_url,
        "label": None,
        "spotify_url": album.get("external_urls", {}).get("spotify"),
        "scraped_at": scraped_at,
    }

    track_params = {
        "original_id": original_id,
        "track_name": track.get("name"),
        "album_id": album.get("id"),
        "duration_ms": track.get("duration_ms"),
        "popularity": track.get("popularity"),
        "explicit": track.get("explicit"),
        "is_local": track.get("is_local"),
        "is_playable": track.get("is_playable", True),
        "track_number": track.get("track_number"),
        "disc_number": track.get("disc_number"),
        "preview_url": track.get("preview_url"),
        "isrc": track.get("external_ids", {}).get("isrc"),
        "spotify_url": track.get("external_urls", {}).get("spotify"),
        "scraped_at": scraped_at,
    }

    album_sql = text("""
        INSERT IGNORE INTO album_metadata (
            album_id,
            album_uri,
            album_name,
            album_type,
            release_date,
            release_date_precision,
            total_tracks,
            album_art_url,
            label,
            spotify_url,
            scraped_at
        )
        VALUES (
            :album_id,
            :album_uri,
            :album_name,
            :album_type,
            :release_date,
            :release_date_precision,
            :total_tracks,
            :album_art_url,
            :label,
            :spotify_url,
            :scraped_at
        )
    """)

    track_sql = text("""
        UPDATE track_metadata
        SET
            track_name = :track_name,
            album_id = :album_id,
            duration_ms = :duration_ms,
            popularity = :popularity,
            explicit = :explicit,
            is_local = :is_local,
            is_playable = :is_playable,
            track_number = :track_number,
            disc_number = :disc_number,
            preview_url = :preview_url,
            isrc = :isrc,
            spotify_url = :spotify_url,
            scraped_at = :scraped_at
        WHERE spotify_id = :original_id
          AND (track_name IS NULL OR TRIM(track_name) = '')
          AND COALESCE(duration_ms, 0) = 0
    """)

    # Both writes share a transaction. Any failure rolls back both.
    with engine.begin() as connection:
        connection.execute(album_sql, album_params)

        result = connection.execute(track_sql, track_params)

        if result.rowcount != 1:
            raise RuntimeError(
                f"Expected to update exactly one malformed row for "
                f"{original_id}, but affected {result.rowcount} rows. "
                "The transaction will be rolled back."
            )

    print("  Metadata repair applied.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply repairs. Without this flag, only validate and preview.",
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"\nMetadata repair mode: {mode}")
    print(f"Tracks in batch: {len(REPAIR_MAP)}\n")

    validated = []

    for original_id, config in REPAIR_MAP.items():
        try:
            track = validate_candidate(original_id, config)
            validated.append((original_id, config, track))
        except Exception as error:
            print(f"SKIPPED {config['track_name']}: {error}")

        time.sleep(0.2)

    print(f"\nValidated: {len(validated)} of {len(REPAIR_MAP)}")

    if not args.apply:
        print("\nDry run only. No database changes were made.")
        print("Review the output before running with --apply.")
        return

    if len(validated) != len(REPAIR_MAP):
        print(
            "\nAborting: not every track passed validation. "
            "No repairs were applied."
        )
        return

    for original_id, config, track in validated:
        repair_track(original_id, config, track, apply_changes=True)

    print("\nRepair batch finished.")


if __name__ == "__main__":
    main()
