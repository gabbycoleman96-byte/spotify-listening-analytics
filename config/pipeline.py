"""
pipeline.py

Author:
    Gabby Coleman

Purpose
-------
Defines the SQL analytics pipeline and Tableau export pipeline.

Keeping these lists in one location allows the ETL to remain
modular. When a new analytics table is added, only this file
needs to be updated.
"""

# ============================================================
# Analytics SQL Execution Order
# ============================================================

ANALYTICS_PIPELINE = [

    ("01_artist_discovery.sql", "artist_discovery"),

    ("02_artist_loyalty.sql", "artist_loyalty"),

    ("03_forgotten_favorites.sql", "forgotten_favorites"),

    ("04_listening_session_summary.sql", "listening_session_summary"),

    ("05_repeat_behavior.sql", "repeat_behavior"),

]

# ============================================================
# Tableau Export Order
# ============================================================

EXPORT_TABLES = [

    "spotify_listening_warehouse",

    "artist_discovery",

    "artist_loyalty",

    "forgotten_favorites",

    "listening_session_summary",

    "repeat_behavior",

    "liked_songs"

]
