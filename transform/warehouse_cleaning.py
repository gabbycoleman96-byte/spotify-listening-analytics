"""
warehouse_cleaning.py

Cleans Spotify listening history before enrichment.

The raw table is never modified.
All cleaning occurs on an in-memory DataFrame.
"""

import pandas as pd
from datetime import timedelta



def remove_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows that are identical across all raw Spotify playback fields.
    """

    print("\nRemoving exact duplicate records...")

    starting_rows = len(df)

    duplicate_columns = [
        "ts",
        "platform",
        "ms_played",
        "conn_country",
        "ip_addr",
        "master_metadata_track_name",
        "master_metadata_album_artist_name",
        "master_metadata_album_album_name",
        "spotify_track_uri",
        "episode_name",
        "episode_show_name",
        "spotify_episode_uri",
        "audiobook_title",
        "audiobook_uri",
        "audiobook_chapter_uri",
        "audiobook_chapter_title",
        "reason_start",
        "reason_end",
        "shuffle",
        "skipped",
        "offline",
        "offline_timestamp",
        "incognito_mode",
    ]

    df = df.drop_duplicates(
        subset=duplicate_columns,
        keep="first"
    ).reset_index(drop=True)

    removed = starting_rows - len(df)

    print(f"Removed {removed:,} exact duplicate records.")

    return df

def remove_duplicate_plays(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes duplicate plays that share the same timestamp and Spotify track.

    If multiple records exist for the same play, the record with the
    largest ms_played is kept.
    """

    print("\nRemoving duplicate plays...")

    starting_rows = len(df)

    df = (
        df.sort_values("ms_played")
        .drop_duplicates(
            subset=["ts", "spotify_track_uri"],
            keep="last",
        )
        .sort_values("ts")
        .reset_index(drop=True)
    )

    removed = starting_rows - len(df)

    print(f"Removed {removed:,} duplicate play records.")

    return df

def remove_impossible_plays(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove playback events that cannot represent real listening activity.

    A play is considered impossible if the same Spotify track begins
    before its previous valid playback could have finished.
    """

    print("\nRemoving impossible playback records...")

    df = df.copy()

    df["ts"] = pd.to_datetime(df["ts"])

    df = (
        df.sort_values("ts")
        .reset_index(drop=True)
    )

    keep = []

    last_valid_tracks = {}

    removed = 0
    
    OVERLAP_TOLERANCE = pd.Timedelta(seconds=2)

    for row in df.itertuples(index=False):

        uri = row.spotify_track_uri

        # Skip anything without a Spotify track URI
        if pd.isna(uri):
            keep.append(True)
            continue

        ts = row.ts
        expected_end = ts + pd.to_timedelta(row.ms_played, unit="ms")

        previous = last_valid_tracks.get(uri)

        if (
            previous is not None
            and ts < (previous["end"] - OVERLAP_TOLERANCE)
        ):

            overlap = previous["end"] - ts


            keep.append(False)
            removed += 1
            continue

        last_valid_tracks[uri] = {
            "start": ts,
            "end": expected_end,
            "track": row.master_metadata_track_name,
            "artist": row.master_metadata_album_artist_name,
        }

        keep.append(True)

    cleaned_df = df.loc[keep].reset_index(drop=True)

    print(f"Removed {removed:,} impossible playback records.")

    return cleaned_df


def normalize_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize nulls, booleans, timestamps, etc.
    """
    return df


def clean_warehouse(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all warehouse cleaning rules.
    """

    print("\nCleaning warehouse...")

    starting_rows = len(df)

    df = remove_exact_duplicates(df)

    df = remove_duplicate_plays(df)

    df = remove_impossible_plays(df)

    df = normalize_values(df)

    ending_rows = len(df)

    print(f"Removed {starting_rows - ending_rows:,} rows.")

    return df