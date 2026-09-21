"""
refresh_warehouse.py

Refreshes the derived warehouse data without rebuilding the
listening-history warehouse from Spotify Extended Streaming
History exports.

Use this for routine updates between full warehouse rebuilds.

Use main.py when a new Spotify Extended Streaming History
export has been received and the warehouse structure needs
to be rebuilt.
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


def refresh_warehouse():

    print("\n" + "=" * 60)
    print("Spotify Warehouse Refresh")
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

    print("\nExporting CSVs...")

    export_tables([
        "album_listening_sequences",
        "listening_history_warehouse"
    ])

    print("\n" + "=" * 60)
    print("Warehouse refresh complete.")
    print("=" * 60)


if __name__ == "__main__":
    refresh_warehouse()