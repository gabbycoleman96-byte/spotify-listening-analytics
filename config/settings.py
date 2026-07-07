"""
settings.py

Central location for project-wide configuration.

Instead of hardcoding folder paths throughout the project,
everything should reference these variables.
"""

from pathlib import Path


# ============================================================
# Project Root
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# Data Folders
# ============================================================

DATA_FOLDER = PROJECT_ROOT / "data"

RAW_DATA_FOLDER = DATA_FOLDER / "raw"

PROCESSED_DATA_FOLDER = DATA_FOLDER / "processed"

EXPORT_FOLDER = DATA_FOLDER / "exports"


# ============================================================
# Raw Data Files
# ============================================================

LIKED_SONGS_FILE = RAW_DATA_FOLDER / "liked_songs.csv"

RECENT_TRACKS_FILE = RAW_DATA_FOLDER / "recent_tracks.csv"

EXPORT_FOLDER = Path("data") / "exports"