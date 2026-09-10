"""
cleanup_liked_songs.py

python -m utils.library_cleanup.cleanup_liked_songs

Purpose
-------
Compare the archived liked-song snapshot against the user's
current Spotify Liked Songs library and identify duplicate
Spotify track versions.

This utility is intentionally separate from the daily ETL.

Current phase:
    - Load archived liked songs
    - Download current Spotify Liked Songs
    - Compare Spotify IDs
    - Enrich records with listening-history information
    - Identify current duplicate Spotify versions
    - Create a review CSV

This phase DOES NOT:
    - Remove anything from Spotify
    - Modify the database
    - Modify liked_songs
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
# Load warehouse enrichment
# ============================================================

def load_song_enrichment():
    """
    Load listening-history information used to evaluate
    duplicate Spotify versions.

    Play count is calculated from the warehouse.

    Canonical information comes from canonical_song_uris.
    """

    query = """
        SELECT
            c.spotify_id,
            c.canonical_uri,
            c.version_count,
            COALESCE(w.play_count, 0) AS play_count
        FROM canonical_song_uris c

        LEFT JOIN (
            SELECT
                spotify_id,
                COUNT(*) AS play_count
            FROM listening_history_warehouse
            GROUP BY spotify_id
        ) w
            ON c.spotify_id = w.spotify_id
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

    stop_at=None forces a full download.
    """

    print(
        "Downloading current Spotify Liked Songs...\n"
    )

    return download_liked_songs(
        stop_at=None
    )


# ============================================================
# Build duplicate groups
# ============================================================

def add_duplicate_information(
    review_df
):
    """
    Identify duplicate Spotify versions among records that
    are currently liked.

    Canonical groups are used when available.

    Records without canonical mappings fall back to normalized
    track name + artist name.
    """

    # --------------------------------------------------------
    # Create fallback normalized song key
    # --------------------------------------------------------

    review_df["normalized_track_name"] = (
        review_df["track_name"]
        .fillna("")
        .str.strip()
        .str.lower()
        .str.replace(
            r"\s+",
            " ",
            regex=True
        )
    )

    review_df["normalized_artist_name"] = (
        review_df["artist_name"]
        .fillna("")
        .str.strip()
        .str.lower()
        .str.replace(
            r"\s+",
            " ",
            regex=True
        )
    )

    # --------------------------------------------------------
    # Use canonical URI when available.
    #
    # Otherwise use normalized track + artist.
    # --------------------------------------------------------

    review_df["duplicate_group"] = (
        review_df["canonical_uri"]
        .fillna(
            "fallback:"
            + review_df["normalized_track_name"]
            + "|"
            + review_df["normalized_artist_name"]
        )
    )

    # --------------------------------------------------------
    # Count currently liked versions in each group
    # --------------------------------------------------------

    active_mask = review_df["currently_liked"]

    active_group_counts = (
        review_df.loc[active_mask]
        .groupby("duplicate_group")["spotify_id"]
        .transform("nunique")
    )

    review_df["liked_version_count"] = 0

    review_df.loc[
        active_mask,
        "liked_version_count"
    ] = active_group_counts

    # --------------------------------------------------------
    # Determine duplicate status
    # --------------------------------------------------------

    review_df["duplicate_status"] = "NOT A DUPLICATE"

    review_df.loc[
        ~review_df["currently_liked"],
        "duplicate_status"
    ] = "NOT ACTIVE"

    review_df.loc[
        active_mask
        & (review_df["liked_version_count"] > 1),
        "duplicate_status"
    ] = "CURRENT DUPLICATE"

    # --------------------------------------------------------
    # Clean up temporary columns
    # --------------------------------------------------------

    review_df = review_df.drop(
        columns=[
            "normalized_track_name",
            "normalized_artist_name"
        ]
    )

    return review_df


# ============================================================
# Build recommendations
# ============================================================

def add_recommendations(review_df):
    """
    Generate conservative cleanup recommendations.

    This function does NOT modify Spotify or the database.
    Recommendations are intended for human review only.
    """

    review_df["action"] = "REVIEW"

    # --------------------------------------------------------
    # Records that are no longer in the current Spotify library
    # --------------------------------------------------------

    review_df.loc[
        ~review_df["currently_liked"],
        "action"
    ] = "ALREADY REMOVED"

    # --------------------------------------------------------
    # Process each currently liked duplicate group
    # --------------------------------------------------------

    active_df = review_df[
        review_df["currently_liked"]
        & (review_df["liked_version_count"] > 1)
    ].copy()

    for group, group_df in active_df.groupby("duplicate_group"):

        # ----------------------------------------------------
        # One version with the highest play count
        # ----------------------------------------------------

        max_play_count = group_df["play_count"].max()

        min_play_count = group_df["play_count"].min()

        # ----------------------------------------------------
        # If there is a zero-play version and another version
        # has listening history, that is a strong candidate
        # for removal.
        # ----------------------------------------------------

        if (
            min_play_count == 0
            and max_play_count > 0
        ):
            zero_play_ids = group_df.loc[
                group_df["play_count"] == 0,
                "spotify_id"
            ]

            review_df.loc[
                review_df["spotify_id"].isin(zero_play_ids),
                "action"
            ] = "REMOVE"

            non_zero_ids = group_df.loc[
                group_df["play_count"] > 0,
                "spotify_id"
            ]

            review_df.loc[
                review_df["spotify_id"].isin(non_zero_ids),
                "action"
            ] = "KEEP"

            continue

        # ----------------------------------------------------
        # Determine whether all versions belong to the same
        # album.
        # ----------------------------------------------------

        album_count = (
            group_df["album_name"]
            .fillna("")
            .nunique()
        )

        # ----------------------------------------------------
        # Same album:
        #
        # If one version has substantially more listening
        # history than the others, recommend keeping it.
        # ----------------------------------------------------

        if album_count == 1:

            sorted_group = group_df.sort_values(
                "play_count",
                ascending=False
            )

            top_play_count = int(
                sorted_group.iloc[0]["play_count"]
            )

            second_play_count = int(
                sorted_group.iloc[1]["play_count"]
            )

            # Strong difference in listening history
            if (
                top_play_count >= 10
                and top_play_count >= second_play_count * 3
            ):
                keep_id = sorted_group.iloc[0]["spotify_id"]

                review_df.loc[
                    review_df["spotify_id"] == keep_id,
                    "action"
                ] = "KEEP"

                remove_ids = sorted_group.iloc[1:][
                    "spotify_id"
                ]

                review_df.loc[
                    review_df["spotify_id"].isin(remove_ids),
                    "action"
                ] = "REMOVE"

            else:
                review_df.loc[
                    review_df["spotify_id"].isin(
                        group_df["spotify_id"]
                    ),
                    "action"
                ] = "MANUAL REVIEW"

        # ----------------------------------------------------
        # Different albums/releases:
        #
        # Do not automatically delete based on play count.
        # ----------------------------------------------------

        else:
            review_df.loc[
                review_df["spotify_id"].isin(
                    group_df["spotify_id"]
                ),
                "action"
            ] = "MANUAL REVIEW"

    # --------------------------------------------------------
    # Non-duplicate currently liked songs
    # --------------------------------------------------------

    review_df.loc[
        review_df["currently_liked"]
        & (review_df["liked_version_count"] == 1),
        "action"
    ] = "KEEP"

    return review_df


# ============================================================
# Build review
# ============================================================

def build_cleanup_review(
    archive_df,
    current_df,
    enrichment_df
):
    """
    Combine archive, live Spotify status, and warehouse
    enrichment into the cleanup review.
    """

    # --------------------------------------------------------
    # Current Spotify IDs
    # --------------------------------------------------------

    current_ids = set(
        current_df["spotify_id"]
        .dropna()
        .astype(str)
    )

    # --------------------------------------------------------
    # Start with archived records
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Add warehouse/canonical information
    # --------------------------------------------------------

    review_df = review_df.merge(
        enrichment_df,
        on="spotify_id",
        how="left"
    )

    review_df["play_count"] = (
        review_df["play_count"]
        .fillna(0)
        .astype(int)
    )

    review_df["liked_version_count"] = 0

    # --------------------------------------------------------
    # Identify duplicates
    # --------------------------------------------------------

    review_df = add_duplicate_information(
        review_df
    )

    # --------------------------------------------------------
    # Generate cleanup recommendations.
    #
    # Recommendations are read-only and require human review.
    # --------------------------------------------------------

    review_df = add_recommendations(
        review_df
    )

    # --------------------------------------------------------
    # Sort so duplicate groups are together.
    # --------------------------------------------------------

    review_df = review_df.sort_values(
        by=[
            "duplicate_status",
            "duplicate_group",
            "play_count"
        ],
        ascending=[
            True,
            True,
            False
        ]
    )

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
# Print results
# ============================================================

def print_results(review_df):
    """
    Print a summary of the duplicate investigation.
    """

    archived_count = len(review_df)

    still_liked_count = int(
        review_df["currently_liked"].sum()
    )

    already_removed_count = (
        archived_count
        - still_liked_count
    )

    duplicate_rows = int(
        (
            review_df["duplicate_status"]
            == "CURRENT DUPLICATE"
        ).sum()
    )

    duplicate_groups = review_df.loc[
        review_df["duplicate_status"]
        == "CURRENT DUPLICATE",
        "duplicate_group"
    ].nunique()

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(
        f"Archived records:             "
        f"{archived_count:,}"
    )

    print(
        f"Currently liked:              "
        f"{still_liked_count:,}"
    )

    print(
        f"Already removed:              "
        f"{already_removed_count:,}"
    )

    print()

    print(
        f"Current duplicate groups:     "
        f"{duplicate_groups:,}"
    )

    print(
        f"Records in duplicate groups:  "
        f"{duplicate_rows:,}"
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


# ============================================================
# Main
# ============================================================

def main():
    """
    Run the read-only duplicate investigation.
    """

    print("=" * 60)
    print("LIKED SONG CLEANUP - DUPLICATE INVESTIGATION")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    # Load archive
    # --------------------------------------------------------

    archive_df = load_archived_liked_songs()

    print(
        f"Archived records loaded: "
        f"{len(archive_df):,}\n"
    )

    # --------------------------------------------------------
    # Load enrichment
    # --------------------------------------------------------

    print(
        "Loading listening-history enrichment...\n"
    )

    enrichment_df = load_song_enrichment()

    print(
        f"Enrichment records loaded: "
        f"{len(enrichment_df):,}\n"
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
    # Build review
    # --------------------------------------------------------

    review_df = build_cleanup_review(
        archive_df,
        current_df,
        enrichment_df
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_review(
        review_df
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print_results(
        review_df
    )


if __name__ == "__main__":
    main()