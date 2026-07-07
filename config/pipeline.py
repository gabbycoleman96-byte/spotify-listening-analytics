"""
pipeline.py

Author:
    Gabby Coleman

Purpose
-------
Defines the analytics pipeline.

Each tuple contains:

    (SQL script, output table)

This keeps SQL execution order and Tableau exports
in one central location.
"""

ANALYTICS_PIPELINE = [

    ("01_yearly_summary.sql", "yearly_summary"),

    ("02_hourly_summary.sql", "hourly_summary"),

    ("03_artist_lifetime_summary.sql", "artist_lifetime_summary"),

    ("04_artist_yearly_summary.sql", "artist_yearly_summary"),

    ("05_track_summary.sql", "track_summary"),

    ("06_liked_song_analysis.sql", "liked_song_analysis"),

]