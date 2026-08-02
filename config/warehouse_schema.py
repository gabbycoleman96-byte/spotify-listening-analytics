"""
warehouse_schema.py

Author:
    Gabby Coleman

Purpose
-------
Defines the Spotify Listening Warehouse schema.

These collections provide a single source of truth for
warehouse column categories and are used throughout the ETL
pipeline.
"""

# ============================================================
# Source Columns
# ============================================================

SOURCE_COLUMNS = {

    # ========================================================
    # Primary Key
    # ========================================================

    "played_at",

    # ========================================================
    # Date / Time
    # ========================================================

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

    # ========================================================
    # Playback Metadata
    # ========================================================

    "ms_played",
    "duration_ms",
    "shuffle_state",
    "skipped",

    # ========================================================
    # Track Metadata
    # ========================================================

    "track_name",
    "artist_name",
    "album_name",
    "spotify_id",
    "spotify_uri",

    # ========================================================
    # Library Metadata
    # ========================================================

    "is_liked",

    # ========================================================
    # Enrichment During Import
    # ========================================================

    "primary_genre",
    "secondary_genre",
    "album_art_url",
    "dominant_color",

    # ========================================================
    # ETL Metadata
    # ========================================================

    "source",
    "imported_at",

}