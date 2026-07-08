"""
dashboard_transform.py

Author:
    Gabby Coleman

Purpose
-------
Transforms raw Spotify API data into the warehouse schema used by
dashboard_data.

This module enriches Spotify playback data with:

- Date dimensions
- Time dimensions
- ETL metadata
- Warehouse-ready column names

The resulting DataFrame can be loaded directly into the
dashboard_data table.
"""

# ============================================================
# Imports
# ============================================================

from datetime import datetime

import pandas as pd


# ============================================================
# Date & Time Dimensions
# ============================================================

def add_date_dimensions(df):
    """
    Add calendar and time dimension columns.
    """

    df = df.copy()

    df["played_at"] = pd.to_datetime(df["played_at"])

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
# Warehouse Defaults
# ============================================================

def add_default_columns(
    df,
    liked_song_ids
):
    """
    Add columns that are not currently supplied
    by the Spotify API.
    """

    df = df.copy()

    # Spotify API does not provide actual playback duration.
    df["ms_played"] = df["duration_ms"]

    df["shuffle_state"] = None

    df["skipped"] = None

    df["is_liked"] = df["spotify_id"].isin(
        liked_song_ids
    )

    df["primary_genre"] = None

    df["secondary_genre"] = None

    df["album_art_url"] = None

    df["dominant_color"] = None

    df["source"] = "Spotify API"

    df["imported_at"] = datetime.now()

    return df



# ============================================================
# Final Column Order
# ============================================================

def reorder_columns(df):
    """
    Arrange columns to match the dashboard_data table.
    """

    return df[

        [

            "played_at",

            "date",

            "year",

            "quarter",

            "month_number",

            "month_name",

            "week",

            "day",

            "weekday_number",

            "weekday_name",

            "hour",

            "hour_label",

            "time",

            "ms_played",

            "duration_ms",

            "shuffle_state",

            "skipped",

            "track_name",

            "artist_name",

            "album_name",

            "spotify_id",

            "spotify_uri",

            "is_liked",

            "primary_genre",

            "secondary_genre",

            "album_art_url",

            "dominant_color",

            "source",

            "imported_at"

        ]

    ]


# ============================================================
# Main Transformation
# ============================================================

def build_dashboard_dataframe(
    df,
    liked_song_ids
):
    """
    Transform raw Spotify API data into the
    dashboard_data warehouse schema.
    """

    df = add_date_dimensions(df)

    df = add_default_columns(
    df,
    liked_song_ids
)

    df = reorder_columns(df)

    return df
