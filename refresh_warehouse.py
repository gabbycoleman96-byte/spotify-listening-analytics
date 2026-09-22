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
    run_liked_songs_stage,
    run_artist_metadata_stage,
    run_track_metadata_stage,
    run_album_art_stage,
    run_warehouse_enrichment_stage,
    run_song_identity_map_stage,
    run_canonical_uri_stage,
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
    # Liked Songs
    # ========================================================

    run_liked_songs_stage()

    # ========================================================
    # Song Identity Map
    # ========================================================

    run_song_identity_map_stage()

    # ========================================================
    # Canonical URI Mapping
    # ========================================================

    run_canonical_uri_stage()

    # ========================================================
    # Artist Metadata
    # ========================================================
    #
    # Temporarily disabled.
    #
    # Keep this stage in the architecture so artist metadata
    # collection can be resumed later if desired.
    #
    # Artist metadata must run BEFORE Track Metadata when
    # enabled so existing artists needing metadata can use
    # the available Spotify API quota before track metadata
    # consumes it.
    #
    # run_artist_metadata_stage()

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
    # Data Export
    # ========================================================

    print("\nExporting warehouse data...")

    export_tables([
        "listening_history_warehouse",
        "liked_songs",
        "album_listening_sequences",
    ])

    print("\n" + "=" * 60)
    print("Warehouse refresh complete.")
    print("=" * 60)


if __name__ == "__main__":
    refresh_warehouse()