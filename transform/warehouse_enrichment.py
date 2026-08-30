"""
warehouse_enrichment.py

Author:
    Gabby Coleman

Purpose
-------
Adds all enrichment fields to the Spotify listening warehouse.
"""

import pandas as pd

from load.reader import read_query


# ============================================================
# Spotify Metadata
# ============================================================

def add_liked_status(df):

    liked_uris = read_query("""
        SELECT DISTINCT
            c.canonical_uri

        FROM canonical_song_uris c

        JOIN liked_songs l
            ON l.spotify_id = c.spotify_id
    """)

    liked_uri_set = set(
        liked_uris["canonical_uri"]
    )

    df["is_liked"] = (
        df["spotify_uri"]
        .isin(liked_uri_set)
    )

    return df


import json


def add_track_metadata(df):

    print("\nAdding track metadata...")

    metadata = read_query("""
        SELECT
            tm.spotify_id AS canonical_spotify_id,
            tm.duration_ms,
            am.album_art_url

        FROM track_metadata tm

        LEFT JOIN album_metadata am
            ON tm.album_id = am.album_id
    """)

    df["canonical_spotify_id"] = (
        df["spotify_uri"]
        .fillna("")
        .str.split(":")
        .str[-1]
        .replace("", None)
    )

    df = df.merge(
        metadata,
        on="canonical_spotify_id",
        how="left",
        suffixes=("", "_metadata"),
    )

    df["duration_ms"] = df["duration_ms_metadata"]
    df["album_art_url"] = df["album_art_url_metadata"]

    df = df.drop(
        columns=[
            "canonical_spotify_id",
            "duration_ms_metadata",
            "album_art_url_metadata",
        ]
    )

    # These enrichments are intentionally not implemented yet.
    for column in [
        "primary_genre",
        "secondary_genre",
        "dominant_color",
    ]:
        if column not in df.columns:
            df[column] = None
    
    print(
        f"Duration populated: "
        f"{df['duration_ms'].notna().sum():,}"
    )

    print(
        f"Album art populated: "
        f"{df['album_art_url'].notna().sum():,}"
    )

    return df

# ============================================================
# Play Numbers
# ============================================================

def add_play_numbers(df):

    df["play_number"] = range(1, len(df) + 1)

    df["play_of_day"] = (
        df.groupby("date").cumcount() + 1
    )

    df["play_of_week"] = (
        df.groupby(["year", "week"]).cumcount() + 1
    )

    df["play_of_month"] = (
        df.groupby(["year", "month_number"]).cumcount() + 1
    )

    df["play_of_year"] = (
        df.groupby("year").cumcount() + 1
    )

    return df


# ============================================================
# Navigation
# ============================================================

def add_navigation_columns(df):

    df["previous_track"] = df["track_name"].shift()
    df["previous_artist"] = df["artist_name"].shift()
    df["previous_album"] = df["album_name"].shift()

    df["next_track"] = df["track_name"].shift(-1)
    df["next_artist"] = df["artist_name"].shift(-1)
    df["next_album"] = df["album_name"].shift(-1)

    df["same_artist_as_previous"] = (
        df["artist_name"] == df["previous_artist"]
    ).fillna(False)

    df["same_album_as_previous"] = (
        df["album_name"] == df["previous_album"]
    ).fillna(False)

    df["same_song_as_previous"] = (
        df["spotify_uri"] == df["spotify_uri"].shift()
    ).fillna(False)

    return df


# ============================================================
# Sessions
# ============================================================

def add_session_columns(df):

    previous = df["played_at"].shift()

    df["minutes_since_previous_play"] = (
        (df["played_at"] - previous)
        .dt.total_seconds()
        / 60
    )

    new_session = (
        previous.isna()
        | (df["minutes_since_previous_play"] >= 30)
    )

    df["session_id"] = new_session.cumsum()

    sessions = (
        df.groupby("session_id")
        .agg(
            session_start=("played_at", "min"),
            session_end=("played_at", "max"),
            session_stream_count=("session_id", "size"),
        )
    )

    sessions["session_duration_minutes"] = (
        (
            sessions["session_end"]
            - sessions["session_start"]
        )
        .dt.total_seconds()
        / 60
    ).round(2)

    for column in sessions.columns:
        df[column] = df["session_id"].map(
            sessions[column]
        )

    df["play_in_session"] = (
        df.groupby("session_id").cumcount() + 1
    )

    df["is_first_play"] = (
        df["play_in_session"] == 1
    )

    df["is_last_play"] = (
        df.groupby("session_id")["play_in_session"]
        .transform("max")
        == df["play_in_session"]
    )

    return df


# ============================================================
# Generic Streak
# ============================================================

def add_streak(df, value, id_col, length_col):

    df[id_col] = (
        df[value]
        .ne(df[value].shift())
        .cumsum()
    )

    df[length_col] = (
        df.groupby(id_col)[id_col]
        .transform("size")
    )

    return df

def add_boolean_streak(df, condition, id_col, length_col):

    streak_id = 0
    current_streak = 0

    ids = []
    lengths = []

    for value in condition:

        if value:

            if current_streak == 0:
                streak_id += 1

            current_streak += 1
            ids.append(streak_id)

        else:

            current_streak = 0
            ids.append(0)

    df[id_col] = ids

    streak_lengths = (
        df[df[id_col] > 0]
        .groupby(id_col)[id_col]
        .transform("size")
    )

    df[length_col] = 0
    df.loc[df[id_col] > 0, length_col] = streak_lengths

    return df

def add_streaks(df):
    
    df["album_key"] = (
    df["artist_name"].fillna("")
    + " | "
    + df["album_name"].fillna("")
)

    streaks = [

    ("artist_name", "artist_streak_id", "artist_streak_length"),
    ("album_key", "album_streak_id", "album_streak_length"),
    ("spotify_uri", "song_streak_id", "song_streak_length"),

    ]

    for value,id_col,length_col in streaks:

        df = add_streak(
            df,
            value,
            id_col,
            length_col,
        )

        df = add_boolean_streak(
            df,
            df["skipped"] == 1,
            "skip_streak_id",
            "skip_streak_length",
        )

    return df


# ============================================================
# Running Counts
# ============================================================

def add_running_counts(df):

    df["artist_play_count"] = (
        df.groupby("artist_name")
        .cumcount()
        + 1
    )

    df["album_play_count"] = (
        df.groupby(["artist_name","album_name"])
        .cumcount()
        + 1
    )
    
    df["album_art_play_count"] = (
        df.groupby("album_art_url")
        ["album_art_url"]
        .transform("size")
    )

    df["track_play_count"] = (
        df.groupby("spotify_uri")
        .cumcount()
        + 1
    )

    return df


# ============================================================
# Final Column Order
# ============================================================

def reorder_columns(df):

    columns = [

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
        
        "is_anomaly",
        "anomaly_type",

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
        "imported_at",

        "session_id",
        "session_start",
        "session_end",
        "session_duration_minutes",
        "session_stream_count",

        "play_number",
        "play_of_day",
        "play_of_week",
        "play_of_month",
        "play_of_year",

        "previous_track",
        "previous_artist",
        "previous_album",

        "next_track",
        "next_artist",
        "next_album",

        "same_artist_as_previous",
        "same_album_as_previous",
        "same_song_as_previous",

        "artist_streak_id",
        "artist_streak_length",

        "album_streak_id",
        "album_streak_length",

        "song_streak_id",
        "song_streak_length",

        "skip_streak_id",
        "skip_streak_length",

        "minutes_since_previous_play",
        "play_in_session",
        "is_first_play",
        "is_last_play",

        "artist_play_count",
        "album_play_count",
        "album_art_play_count",
        "track_play_count",
    ]

    for column in columns:

        if column not in df.columns:
            df[column] = None

    return df[columns]

# ============================================================
# Data Quality
# ============================================================

def add_data_quality_flags(df):

    print("\nAdding data quality flags...")

    df["is_anomaly"] = 0
    df["anomaly_type"] = None

    repeating_loop_tracks = [
        "Everybody Talks",
        "Champion",
        "Young Volcanoes",
        "Body Talks (feat. Kesha)",
        "Could Have Been Me",
    ]

    repeating_loop = (
        (df["played_at"] >= pd.Timestamp("2022-07-05 03:35:45"))
        & (df["played_at"] <= pd.Timestamp("2022-07-05 22:16:47"))
        & (df["track_name"].isin(repeating_loop_tracks))
    )

    df.loc[repeating_loop, "is_anomaly"] = 1
    df.loc[repeating_loop, "anomaly_type"] = (
        "repeating_playback_loop"
    )

    flagged = repeating_loop.sum()

    print(
        f"Flagged {flagged:,} anomalous playback records."
    )

    return df

# ============================================================
# Master
# ============================================================

def enrich_warehouse(df):

    print("\nEnriching warehouse...")

    df = (
        df.sort_values("played_at")
        .reset_index(drop=True)
    )

    df = add_liked_status(df)
    df = add_track_metadata(df)
    df = add_data_quality_flags(df)
    df = add_play_numbers(df)
    df = add_navigation_columns(df)
    df = add_session_columns(df)
    df = add_streaks(df)
    df = add_running_counts(df)

    return reorder_columns(df)

