"""
refresh_dashboard.py

Refreshes the metadata and album analytics needed for
the Tableau dashboard without rebuilding the listening
history warehouse.

Use this for normal dashboard updates when metadata
needs to be refreshed without rebuilding the listening
history warehouse.

Use main.py instead when a new Spotify Extended Streaming
History export has been received.
"""

from pathlib import Path

from main import (
    run_track_metadata_stage,
    run_artist_metadata_stage,
    run_album_art_stage,
    run_warehouse_enrichment_stage,
)

from load.loader import execute_sql_file
from export.export_csv import export_tables


ANALYSIS_FILE = (
    Path("sql")
    / "analysis"
    / "08_album_listening_sequences.sql"
)


def refresh_dashboard():

    print("\n" + "=" * 60)
    print("Spotify Dashboard Refresh")
    print("=" * 60)

    # ========================================================
    # Artist Metadata
    # ========================================================
    
    run_artist_metadata_stage()

    # ========================================================
    # Track Metadata
    # ========================================================

    run_track_metadata_stage()

    # ========================================================
    # Album Art
    # ========================================================

    run_album_art_stage()

    # ========================================================
    # Warehouse Enrichment
    # ========================================================

    run_warehouse_enrichment_stage()

    # ========================================================
    # Album Listening Sequences
    # ========================================================

    print("\nRebuilding album listening sequences...")

    execute_sql_file(ANALYSIS_FILE)

    # ========================================================
    # Tableau Export
    # ========================================================

    print("\nExporting album listening sequences...")

    export_tables([
        "album_listening_sequences"
    ])

    print("\n" + "=" * 60)
    print("Dashboard refresh complete.")
    print("=" * 60)


if __name__ == "__main__":
    refresh_dashboard()