"""
investigate_zero_play_songs.py

One-off investigation of liked songs that currently show
0 plays in the cleanup review.

Purpose:
    Find whether these songs have listening history under
    different Spotify track IDs.

This script:
    - Reads the 279-song CSV
    - Creates normalized track/artist matching keys
    - Matches those songs against the listening warehouse
    - Returns every Spotify version found in the warehouse
    - Calculates play count, first play, and last play

This script DOES NOT:
    - Modify Spotify
    - Modify the database
    - Modify liked_songs
    - Modify the cleanup review
"""

from pathlib import Path

import pandas as pd

from load.database import engine


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "manual"
    / "279 without plays - liked_song_cleanup_review.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "manual"
    / "279_zero_play_warehouse_investigation.csv"
)


# ============================================================
# Normalization
# ============================================================

def normalize_text(series):
    """
    Normalize text for matching track/artist names.

    This follows the same basic normalization used by the
    liked-song cleanup script.
    """

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


# ============================================================
# Load 279 songs
# ============================================================

def load_zero_play_songs():
    """
    Load the manually exported 279-song investigation file.
    """

    print("Loading 279 zero-play songs...")

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded {len(df):,} records."
    )

    df["match_track"] = normalize_text(
        df["track_name"]
    )

    df["match_artist"] = normalize_text(
        df["artist_name"]
    )

    return df


# ============================================================
# Load warehouse matches
# ============================================================

def find_warehouse_matches(zero_play_df):
    """
    Find all listening-history records matching the 279 songs
    by normalized track name + artist name.

    We aggregate at the Spotify track-ID level so different
    Spotify versions remain visible.
    """

    print()
    print("Searching listening warehouse...")
    print()

    # --------------------------------------------------------
    # Build the list of unique track/artist combinations.
    # --------------------------------------------------------

    match_keys = (
        zero_play_df[
            [
                "match_track",
                "match_artist"
            ]
        ]
        .drop_duplicates()
    )

    # --------------------------------------------------------
    # Load only the warehouse columns needed for this
    # investigation.
    # --------------------------------------------------------

    query = """
        SELECT
            spotify_id,
            track_name,
            artist_name,
            album_name,
            duration_ms,
            played_at
        FROM listening_history_warehouse
    """

    warehouse_df = pd.read_sql(
        query,
        engine
    )

    print(
        f"Warehouse records loaded: "
        f"{len(warehouse_df):,}"
    )

    # --------------------------------------------------------
    # Normalize warehouse track and artist names.
    # --------------------------------------------------------

    warehouse_df["match_track"] = normalize_text(
        warehouse_df["track_name"]
    )

    warehouse_df["match_artist"] = normalize_text(
        warehouse_df["artist_name"]
    )

    # --------------------------------------------------------
    # Keep only warehouse records whose normalized
    # track/artist combination exists in our 279 songs.
    # --------------------------------------------------------

    warehouse_df = warehouse_df.merge(
        match_keys,
        on=[
            "match_track",
            "match_artist"
        ],
        how="inner"
    )

    print(
        f"Matching warehouse records found: "
        f"{len(warehouse_df):,}"
    )

    # --------------------------------------------------------
    # Aggregate by Spotify version.
    # --------------------------------------------------------

    result_df = (
        warehouse_df
        .groupby(
            [
                "match_track",
                "match_artist",
                "spotify_id",
                "track_name",
                "artist_name",
                "album_name",
                "duration_ms"
            ],
            dropna=False
        )
        .agg(
            warehouse_play_count=(
                "played_at",
                "count"
            ),
            first_played=(
                "played_at",
                "min"
            ),
            last_played=(
                "played_at",
                "max"
            )
        )
        .reset_index()
    )

    return result_df


# ============================================================
# Combine liked-song records with warehouse results
# ============================================================

def build_investigation(zero_play_df, warehouse_df):
    """
    Combine the original liked-song information with every
    warehouse version found for that song.
    """

    columns_to_keep = [
        "spotify_id",
        "track_name",
        "artist_name",
        "album_name",
        "release_date",
        "added_to_library",
        "duration_ms",
    ]

    liked_df = zero_play_df[
        columns_to_keep
    ].copy()

    liked_df = liked_df.rename(
        columns={
            "spotify_id": "liked_spotify_id",
            "album_name": "liked_album_name",
            "duration_ms": "liked_duration_ms"
        }
    )

    liked_df["match_track"] = normalize_text(
        liked_df["track_name"]
    )

    liked_df["match_artist"] = normalize_text(
        liked_df["artist_name"]
    )

    # --------------------------------------------------------
    # Left join so songs with genuinely NO warehouse history
    # still appear in the output.
    # --------------------------------------------------------

    result_df = liked_df.merge(
        warehouse_df,
        on=[
            "match_track",
            "match_artist"
        ],
        how="left",
        suffixes=(
            "",
            "_warehouse"
        )
    )

    # --------------------------------------------------------
    # Identify whether the warehouse version is the exact
    # Spotify ID that appears in the liked-song record.
    # --------------------------------------------------------

    result_df["same_spotify_id"] = (
        result_df["liked_spotify_id"]
        == result_df["spotify_id"]
    )

    # --------------------------------------------------------
    # Make the important status obvious.
    # --------------------------------------------------------

    result_df["warehouse_status"] = "NO WAREHOUSE HISTORY"

    result_df.loc[
        result_df["spotify_id"].notna(),
        "warehouse_status"
    ] = "PLAYED VERSION FOUND"

    result_df.loc[
        result_df["same_spotify_id"],
        "warehouse_status"
    ] = "LIKED VERSION PLAYED"

    # --------------------------------------------------------
    # Sort each song's versions by play count.
    # --------------------------------------------------------

    result_df = result_df.sort_values(
        by=[
            "track_name",
            "artist_name",
            "warehouse_play_count"
        ],
        ascending=[
            True,
            True,
            False
        ],
        na_position="last"
    )

    # --------------------------------------------------------
    # Remove temporary matching columns.
    # --------------------------------------------------------

    result_df = result_df.drop(
        columns=[
            "match_track",
            "match_artist"
        ]
    )

    return result_df


# ============================================================
# Save results
# ============================================================

def save_results(result_df):
    """
    Save investigation results to CSV.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(
        f"Investigation saved to:"
    )
    print(
        OUTPUT_FILE
    )


# ============================================================
# Print summary
# ============================================================

def print_summary(result_df):
    """
    Print a concise investigation summary.
    """

    total_songs = (
        result_df["liked_spotify_id"]
        .nunique()
    )

    songs_with_history = (
        result_df.loc[
            result_df["spotify_id"].notna(),
            "liked_spotify_id"
        ]
        .nunique()
    )

    songs_without_history = (
        total_songs
        - songs_with_history
    )

    alternate_version_count = (
        result_df.loc[
            result_df["spotify_id"].notna()
            & ~result_df["same_spotify_id"],
            "liked_spotify_id"
        ]
        .nunique()
    )

    exact_version_count = (
        result_df.loc[
            result_df["same_spotify_id"],
            "liked_spotify_id"
        ]
        .nunique()
    )

    print()
    print("=" * 60)
    print("ZERO-PLAY SONG INVESTIGATION")
    print("=" * 60)

    print(
        f"Songs investigated:                 "
        f"{total_songs:,}"
    )

    print(
        f"Songs with warehouse history:       "
        f"{songs_with_history:,}"
    )

    print(
        f"Songs with NO warehouse history:    "
        f"{songs_without_history:,}"
    )

    print(
        f"Songs played under another ID:      "
        f"{alternate_version_count:,}"
    )

    print(
        f"Songs played under liked ID:        "
        f"{exact_version_count:,}"
    )

    print("=" * 60)


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("INVESTIGATING 279 ZERO-PLAY LIKED SONGS")
    print("=" * 60)
    print()

    zero_play_df = load_zero_play_songs()

    warehouse_df = find_warehouse_matches(
        zero_play_df
    )

    result_df = build_investigation(
        zero_play_df,
        warehouse_df
    )

    save_results(
        result_df
    )

    print_summary(
        result_df
    )


if __name__ == "__main__":
    main()