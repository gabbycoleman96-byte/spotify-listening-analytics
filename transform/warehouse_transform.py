"""
warehouse_transform.py

Author:
    Gabby Coleman

Purpose
-------
Build the Spotify listening warehouse from the raw listening history.

Pipeline
--------
1. Load raw listening history
2. Clean raw data
3. Rename Spotify export columns
4. Extract Spotify IDs
5. Add date/time dimensions
6. Add warehouse metadata
7. Return warehouse-ready DataFrame
"""

# ============================================================
# Imports
# ============================================================

from datetime import datetime

import pandas as pd

from load.reader import read_table
from transform.warehouse_cleaning import clean_warehouse
from transform.warehouse_enrichment import enrich_warehouse


# ============================================================
# Raw History
# ============================================================

def load_raw_history():
    """
    Load the complete raw listening history from MySQL.
    """

    print("\nLoading raw listening history...")

    return read_table("listening_history_raw")


# ============================================================
# Raw Column Mapping
# ============================================================

def rename_raw_columns(df):
    """
    Rename Spotify export columns to warehouse column names.
    """

    df = df.rename(
        columns={
            "ts": "played_at",
            "master_metadata_track_name": "track_name",
            "master_metadata_album_artist_name": "artist_name",
            "master_metadata_album_album_name": "album_name",
            "spotify_track_uri": "spotify_uri",
            "shuffle": "shuffle_state",
        }
    )

    return df


# ============================================================
# Spotify ID
# ============================================================

def extract_spotify_ids(df):
    """
    Extract the Spotify ID from spotify:track: URIs.
    """

    df = df.copy()

    df["spotify_id"] = (
        df["spotify_uri"]
        .fillna("")
        .str.split(":")
        .str[-1]
        .replace("", None)
    )

    return df


# ============================================================
# Date Dimensions
# ============================================================

def add_date_dimensions(df):

    df = df.copy()

    # Use the actual offline playback timestamp when available.
    # Spotify has exported offline_timestamp in both Unix seconds
    # and Unix milliseconds across different records.

    offline_mask = (
        (df["offline"] == 1)
        & (df["offline_timestamp"].notna())
    )

    df["played_at"] = pd.to_datetime(
        df["played_at"],
        format="mixed"
    )

    offline_values = pd.to_numeric(
        df.loc[offline_mask, "offline_timestamp"],
        errors="coerce"
    )

    milliseconds_mask = offline_values >= 100_000_000_000

    df.loc[
        offline_values.index[milliseconds_mask],
        "played_at"
    ] = pd.to_datetime(
        offline_values[milliseconds_mask],
        unit="ms"
    )

    df.loc[
        offline_values.index[~milliseconds_mask],
        "played_at"
    ] = pd.to_datetime(
        offline_values[~milliseconds_mask],
        unit="s"
    )

    df["date"] = df["played_at"].dt.date
    df["year"] = df["played_at"].dt.year
    df["quarter"] = df["played_at"].dt.quarter
    df["month_number"] = df["played_at"].dt.month
    df["month_name"] = df["played_at"].dt.month_name()
    df["week"] = df["played_at"].dt.isocalendar().week.astype(int)
    df["day"] = df["played_at"].dt.day
    df["weekday_number"] = df["played_at"].dt.weekday + 1
    df["weekday_name"] = df["played_at"].dt.day_name()
    df["hour"] = df["played_at"].dt.hour

    df["hour_label"] = (
        df["played_at"]
        .dt.strftime("%I %p")
        .str.lstrip("0")
    )

    df["time"] = df["played_at"].dt.time

    return df


# ============================================================
# Warehouse Metadata
# ============================================================

def add_metadata(df):
    """
    Add ETL metadata columns.
    """

    df = df.copy()

    df["imported_at"] = datetime.now()

    return df


# ============================================================
# Main Builder
# ============================================================

def build_warehouse_dataframe():
    """
    Build the warehouse dataframe from raw Spotify history.
    """

    df = load_raw_history()

    df = clean_warehouse(df)
    
    dupes = df[df.duplicated(
        subset=["ts", "spotify_track_uri"],
        keep=False
    )]

    df = rename_raw_columns(df)

    df = extract_spotify_ids(df)

    df = add_date_dimensions(df)

    df = add_metadata(df)

    # Remove rows with no music metadata
    before = len(df)

    df = df[
        df["track_name"].notna()
        & df["artist_name"].notna()
        & df["spotify_uri"].notna()
    ].copy()

    print(f"Removed {before - len(df):,} rows with no track metadata.")

    df = enrich_warehouse(df)

    return df