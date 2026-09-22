"""
Apply canonical Spotify song identities to the warehouse.

The permanent song_identity_map is the authoritative source
for Spotify song identity.

This module:

1. Rebuilds canonical_song_uris from song_identity_map.
2. Updates listening_history_warehouse in batches.
3. Verifies that no warehouse rows remain mismatched.

The warehouse update is intentionally chunked so the ETL can
display real progress instead of appearing frozen during a
large MySQL UPDATE.
"""

from __future__ import annotations

from time import perf_counter

from sqlalchemy import text
from tqdm import tqdm

from load.database import engine


BATCH_SIZE = 5_000


def rebuild_canonical_song_uris():
    """Rebuild the compatibility mapping from the identity map."""

    with engine.begin() as connection:

        connection.execute(
            text(
                """
                DROP TABLE IF EXISTS canonical_song_uris
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE canonical_song_uris AS
                SELECT
                    spotify_id,
                    CONCAT(
                        'spotify:track:',
                        canonical_spotify_id
                    ) AS canonical_uri,
                    COUNT(*) OVER (
                        PARTITION BY canonical_spotify_id
                    ) AS version_count
                FROM song_identity_map
                WHERE canonical_spotify_id IS NOT NULL
                """
            )
        )

        connection.execute(
            text(
                """
                ALTER TABLE canonical_song_uris
                ADD INDEX idx_canonical_song_uris_spotify_id (
                    spotify_id
                )
                """
            )
        )


def count_mismatches() -> int:
    """Count warehouse rows whose URI differs from the canonical URI."""

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM listening_history_warehouse AS w
                JOIN canonical_song_uris AS c
                    ON w.spotify_id = c.spotify_id
                WHERE w.spotify_uri <> c.canonical_uri
                """
            )
        )

        return int(result.scalar() or 0)


def update_warehouse_in_batches(
    total_mismatches: int,
):
    """Apply canonical URIs in batches with a real progress bar."""

    if total_mismatches == 0:
        print("Warehouse already uses canonical Spotify URIs.")
        return

    updated_total = 0

    with tqdm(
        total=total_mismatches,
        desc="Canonical URI mapping",
        unit="rows",
        dynamic_ncols=True,
    ) as progress:

        while True:

            with engine.begin() as connection:

                result = connection.execute(
                    text(
                        f"""
                        UPDATE listening_history_warehouse AS w
                        JOIN canonical_song_uris AS c
                            ON w.spotify_id = c.spotify_id
                        SET w.spotify_uri = c.canonical_uri
                        WHERE w.spotify_uri <> c.canonical_uri
                        LIMIT {BATCH_SIZE}
                        """
                    )
                )

                updated = result.rowcount or 0

            if updated == 0:
                break

            updated_total += updated
            progress.update(updated)

    if updated_total != total_mismatches:
        raise RuntimeError(
            "Canonical URI update count changed during processing. "
            f"Expected {total_mismatches:,}, "
            f"updated {updated_total:,}."
        )


def verify_canonical_mapping():
    """Verify that every mapped warehouse row now uses its canonical URI."""

    with engine.connect() as connection:

        remaining_mismatches = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM listening_history_warehouse AS w
                JOIN canonical_song_uris AS c
                    ON w.spotify_id = c.spotify_id
                WHERE w.spotify_uri <> c.canonical_uri
                """
            )
        ).scalar()

        duplicate_spotify_ids = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT spotify_id
                    FROM canonical_song_uris
                    GROUP BY spotify_id
                    HAVING COUNT(*) > 1
                ) duplicates
                """
            )
        ).scalar()

    if remaining_mismatches:
        raise RuntimeError(
            "Canonical URI verification failed. "
            f"{remaining_mismatches:,} mismatches remain."
        )

    if duplicate_spotify_ids:
        raise RuntimeError(
            "Canonical URI verification failed. "
            f"{duplicate_spotify_ids:,} duplicate Spotify IDs found."
        )


def apply_canonical_song_uris():
    """Rebuild canonical mapping and apply it to the warehouse."""

    stage_start = perf_counter()

    print("\nRebuilding canonical song mapping...")

    rebuild_canonical_song_uris()

    total_mismatches = count_mismatches()

    print(
        f"Rows requiring canonical URI updates: "
        f"{total_mismatches:,}"
    )

    update_warehouse_in_batches(
        total_mismatches
    )

    print("Verifying canonical URI mapping...")

    verify_canonical_mapping()

    runtime = perf_counter() - stage_start

    print(
        f"Canonical URI mapping complete "
        f"({runtime:.2f}s)"
    )