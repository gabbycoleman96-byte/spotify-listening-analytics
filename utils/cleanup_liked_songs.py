"""
cleanup_liked_songs.py

Purpose
-------
Create a safe, read-only comparison between the archived liked-song
snapshot and the user's current Spotify Liked Songs library.

This utility is intentionally separate from the daily ETL.

PHASE 1:
    - Read archived liked songs from MySQL
    - Download the current Spotify Liked Songs library
    - Compare Spotify IDs
    - Identify records that have already been removed
    - Create a review CSV

This phase DOES NOT:
    - Remove anything from Spotify
    - Modify the database
    - Modify liked_songs

The destructive cleanup step will be added only after this
comparison has been verified.
"""

# ============================================================
# Imports
# ============================================================

from pathlib import Path

import pandas as pd

from extract.liked_songs import download_liked_songs
from load.database import engine


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ARCHIVE_TABLE = "liked_songs_archive_20260905"

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "liked_song_cleanup_review.csv"
)


# ============================================================
# Load archived library
# ============================================================

def load_archived_liked_songs():
    """
    Load the preserved pre-cleanup liked-song snapshot.
    """

    query = f"""
        SELECT
            spotify_id,
            track_name,
            artist_name,
            album_name,
            release_date,
            added_to_library,
            duration_ms,
            popularity,
            spotify_uri
        FROM {ARCHIVE_TABLE}
    """

    return pd.read_sql(
        query,
        engine
    )


# ============================================================
# Load current Spotify library
# ============================================================

def load_current_liked_songs():
    """
    Download the user's complete current Spotify Liked Songs
    library.

    stop_at=None forces the existing extractor to perform a
    full download instead of an incremental download.
    """

    print("Downloading current Spotify Liked Songs...\n")

    return download_liked_songs(
        stop_at=None
    )


# ============================================================
# Compare libraries
# ============================================================

def build_cleanup_review(
    archive_df,
    current_df
):
    """
    Compare archived Spotify IDs against the current Spotify
    library.
    """

    current_ids = set(
        current_df["spotify_id"]
        .dropna()
        .astype(str)
    )

    review_df = archive_df.copy()

    review_df["currently_liked"] = (
        review_df["spotify_id"]
        .astype(str)
        .isin(current_ids)
    )

    review_df["current_spotify_status"] = (
        review_df["currently_liked"]
        .map(
            {
                True: "CURRENTLY LIKED",
                False: "ALREADY REMOVED"
            }
        )
    )

    # Nothing gets automatically classified for removal yet.
    review_df["action"] = "REVIEW"

    return review_df


# ============================================================
# Save review
# ============================================================

def save_review(review_df):
    """
    Save the cleanup review CSV.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    review_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"Review file created:\n"
        f"{OUTPUT_FILE}\n"
    )


# ============================================================
# Main
# ============================================================

def main():
    """
    Run the read-only liked-library comparison.
    """

    print("=" * 60)
    print("LIKED SONG CLEANUP - DRY RUN")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Load archived snapshot
    # --------------------------------------------------------

    archive_df = load_archived_liked_songs()

    print(
        f"Archived records loaded: "
        f"{len(archive_df):,}\n"
    )

    # --------------------------------------------------------
    # Download current Spotify library
    # --------------------------------------------------------

    current_df = load_current_liked_songs()

    print(
        f"\nCurrent Spotify records: "
        f"{len(current_df):,}\n"
    )

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    review_df = build_cleanup_review(
        archive_df,
        current_df
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_review(review_df)

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    archived_count = len(archive_df)

    current_count = len(current_df)

    still_liked_count = (
        review_df["currently_liked"]
        .sum()
    )

    already_removed_count = (
        ~review_df["currently_liked"]
    ).sum()

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(
        f"Archived records:             "
        f"{archived_count:,}"
    )

    print(
        f"Current Spotify records:      "
        f"{current_count:,}"
    )

    print(
        f"Archived records still liked: "
        f"{still_liked_count:,}"
    )

    print(
        f"Already removed:              "
        f"{already_removed_count:,}"
    )

    print()

    print(
        "Spotify changes made:          0"
    )

    print(
        "Database changes made:         0"
    )

    print()

    print(
        "This was a READ-ONLY dry run."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()