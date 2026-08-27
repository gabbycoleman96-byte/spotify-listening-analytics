"""
main.py

Author:
    Gabby Coleman

Purpose
-------
Runs the complete Listening History ETL pipeline.

Pipeline
--------
1. Check for new liked songs
2. Download new liked songs
3. Load liked songs into MySQL
4. Download recent tracks
5. Refresh recent tracks snapshot
6. Append new plays to listening_history_raw
7. Rebuild listening_history_warehouse
8. Rebuild analytics tables
9. Export Tableau datasets
10. Log the ETL run
"""

# ============================================================
# Imports
# ============================================================

from dataclasses import dataclass
from datetime import datetime, time
from time import perf_counter
from pathlib import Path

from extract.liked_songs import download_liked_songs
from extract.recent_tracks import download_recent_tracks

from load.database import get_latest_liked_song_date
from load.etl_logger import log_etl_run
from load.loader import (
    execute_sql,
    execute_sql_file,
    load_dataframe,
)

from load.load_artist_metadata import (
    get_missing_artist_ids,
    download_artist_metadata,
    update_artist_metadata,
)

from transform.warehouse_transform import (
    build_warehouse_dataframe,
    rebuild_warehouse_enrichment,
)

from transform.rebuild_summary_tables import (
    rebuild_analytics_tables,
)

from export.export_csv import export_tables

from config.pipeline import EXPORT_TABLES

from load.load_track_metadata import load_track_metadata

from utils.album_art_manager import process_album_art


# ============================================================
# Main ETL Pipeline
# ============================================================


def print_pipeline_header():
    print("=" * 60)
    print("Listening History ETL Pipeline")
    print("=" * 60)


@dataclass
class StageResult:
    downloaded: int = 0
    inserted: int = 0
    rows_loaded: int = 0
    runtime: float = 0.0


def format_runtime(seconds):
    if seconds >= 60:
        minutes = int(seconds // 60)
        seconds = seconds - (minutes * 60)
        return f"{minutes}m {seconds:.2f}s"

    return f"{seconds:.2f}s"


def print_stage_header(stage_index, total_stages, stage_name):
    print("\n" + "=" * 60)
    print(f"[{stage_index}/{total_stages}] {stage_name}")
    print("=" * 60)


def print_stage_complete(stage_name, runtime):
    print(f"Completed {stage_name} in {format_runtime(runtime)}")


def print_performance_summary(stage_results, total_runtime):
    print("\n" + "=" * 60)
    print("ETL Performance")
    print("=" * 60)

    for stage_name, result in stage_results:
        print(f"{stage_name:<40}{format_runtime(result.runtime)}")

    print("-" * 60)
    print(f"{'Total Runtime':<40}{format_runtime(total_runtime)}")
    print("\nPipeline completed successfully!")


def run_liked_songs_stage():
    stage_start = perf_counter()

    stage_name = "Liked Songs"
    print_stage_header(1, 9, stage_name)
    print("Checking for new liked songs...")

    latest_liked_song = get_latest_liked_song_date()

    if latest_liked_song is None:
        print("No liked songs found.")
        print("Performing full download...\n")
    else:
        print(f"Latest liked song: {latest_liked_song}")
        print("Performing incremental download...\n")

    liked_df = download_liked_songs(stop_at=latest_liked_song)
    liked_downloaded = len(liked_df)
    liked_inserted = 0

    if liked_downloaded > 0:
        liked_inserted = load_dataframe(
            liked_df,
            "liked_songs",
            ignore_duplicates=True,
        )
    else:
        print("No new liked songs.")

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(
        downloaded=liked_downloaded,
        inserted=liked_inserted,
        runtime=stage_runtime,
    )


def run_recent_tracks_stage():
    stage_start = perf_counter()

    stage_name = "Recent Tracks"
    print_stage_header(2, 9, stage_name)
    print("Downloading recently played tracks...")

    recent_df = download_recent_tracks()
    recent_downloaded = len(recent_df)

    print("Refreshing recent tracks snapshot...")
    execute_sql(
        """
            TRUNCATE TABLE recent_50_tracks_snapshot;
        """
    )

    load_dataframe(
        recent_df,
        "recent_50_tracks_snapshot",
    )

    print("Preparing recent tracks for raw history...")

    recent_raw_df = recent_df.rename(
        columns={
            "played_at": "ts",
            "track_name": "master_metadata_track_name",
            "artist_name": "master_metadata_album_artist_name",
            "album_name": "master_metadata_album_album_name",
            "spotify_uri": "spotify_track_uri",
            "duration_ms": "ms_played",
        }
    ).copy()

    # Populate Spotify export columns not available through the Spotify Web API
    recent_raw_df["platform"] = None
    recent_raw_df["conn_country"] = None
    recent_raw_df["ip_addr"] = None

    recent_raw_df["episode_name"] = None
    recent_raw_df["episode_show_name"] = None
    recent_raw_df["spotify_episode_uri"] = None

    recent_raw_df["audiobook_title"] = None
    recent_raw_df["audiobook_uri"] = None
    recent_raw_df["audiobook_chapter_uri"] = None
    recent_raw_df["audiobook_chapter_title"] = None

    recent_raw_df["reason_start"] = None
    recent_raw_df["reason_end"] = None

    recent_raw_df["shuffle"] = None
    recent_raw_df["skipped"] = None
    recent_raw_df["offline"] = None
    recent_raw_df["offline_timestamp"] = None
    recent_raw_df["incognito_mode"] = None
    recent_raw_df["source"] = "Spotify API"

    # Match raw table column order
    recent_raw_df = recent_raw_df[
        [
            "ts",
            "platform",
            "ms_played",
            "conn_country",
            "ip_addr",
            "master_metadata_track_name",
            "master_metadata_album_artist_name",
            "master_metadata_album_album_name",
            "spotify_track_uri",
            "episode_name",
            "episode_show_name",
            "spotify_episode_uri",
            "audiobook_title",
            "audiobook_uri",
            "audiobook_chapter_uri",
            "audiobook_chapter_title",
            "reason_start",
            "reason_end",
            "shuffle",
            "skipped",
            "offline",
            "offline_timestamp",
            "incognito_mode",
            "source",
        ]
    ]

    print("Appending new listening history...")
    recent_inserted = load_dataframe(
        recent_raw_df,
        "listening_history_raw",
        ignore_duplicates=True,
    )

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(
        downloaded=recent_downloaded,
        inserted=recent_inserted,
        runtime=stage_runtime,
    )


def run_track_metadata_stage():
    stage_start = perf_counter()

    stage_name = "Track Metadata"
    print_stage_header(3, 9, stage_name)
    print("Downloading metadata for new tracks...")

    metadata = load_track_metadata()

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    rows_loaded = (
        len(metadata["tracks"])
        if isinstance(metadata, dict)
        else len(metadata)
    )

    return StageResult(
        rows_loaded=rows_loaded,
        runtime=stage_runtime,
    )
    
    
def run_artist_metadata_stage():
    stage_start = perf_counter()

    stage_name = "Artist Metadata"
    print_stage_header(4, 9, stage_name)
    print("Downloading metadata for new artists...")

    artist_ids = get_missing_artist_ids()

    if not artist_ids:
        print("No new artists require metadata.")

        stage_runtime = perf_counter() - stage_start
        print_stage_complete(stage_name, stage_runtime)

        return StageResult(
            rows_loaded=0,
            runtime=stage_runtime,
        )

    metadata = download_artist_metadata(artist_ids)

    rows_updated = update_artist_metadata(metadata)

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(
        rows_loaded=rows_updated,
        runtime=stage_runtime,
    )    
    
    
def run_album_art_stage():
    stage_start = perf_counter()

    stage_name = "Album Art"
    print_stage_header(5, 9, stage_name)
    print("Updating album artwork...")

    rows_loaded = process_album_art()

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(
        rows_loaded=rows_loaded,
        runtime=stage_runtime,
    )


def run_warehouse_stage():
    stage_start = perf_counter()

    stage_name = "Listening History Warehouse"
    print_stage_header(6, 9, stage_name)
    print("Rebuilding listening history warehouse...")

    warehouse_df = build_warehouse_dataframe()
    duplicates = (
        warehouse_df[
            warehouse_df.duplicated(
                subset=["played_at", "spotify_id"],
                keep=False,
            )
        ]
        .sort_values(["played_at", "spotify_id"])
    )

    print(f"\nFound {len(duplicates)} duplicate warehouse rows:\n")
    print("Replacing warehouse...")

    execute_sql(
        """
            TRUNCATE TABLE listening_history_warehouse;
        """
    )

    warehouse_inserted = load_dataframe(
        warehouse_df,
        "listening_history_warehouse",
    )
    
    print("\nNormalizing Spotify song URIs...")

    execute_sql_file(
        Path("sql")
        / "analysis"
        / "09_normalize_song_uris.sql"
    )

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(
        rows_loaded=warehouse_inserted,
        runtime=stage_runtime,
    )


def run_warehouse_enrichment_stage():
    stage_start = perf_counter()

    stage_name = "Warehouse Enrichment"
    print_stage_header(7, 9, stage_name)
    print("Rebuilding warehouse enrichment...")

    enriched_df = rebuild_warehouse_enrichment()

    execute_sql(
        """
            TRUNCATE TABLE listening_history_warehouse;
        """
    )

    rows_loaded = load_dataframe(
        enriched_df,
        "listening_history_warehouse",
    )

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(
        rows_loaded=rows_loaded,
        runtime=stage_runtime,
    )


def run_analytics_stage():
    stage_start = perf_counter()

    stage_name = "Analytics"
    print_stage_header(8, 9, stage_name)
    print("Rebuilding analytics tables...")

    rebuild_analytics_tables()

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(runtime=stage_runtime)


def run_export_stage():
    stage_start = perf_counter()

    stage_name = "Tableau Export"
    print_stage_header(9, 9, stage_name)
    print("Exporting Tableau datasets...")

    export_tables(EXPORT_TABLES)

    stage_runtime = perf_counter() - stage_start
    print_stage_complete(stage_name, stage_runtime)

    return StageResult(runtime=stage_runtime)


def main():
    """Run the complete Listening History ETL pipeline."""

    pipeline_start = perf_counter()
    pipeline_start_time = datetime.now()

    status = "Success"
    error_message = None

    try:
        print_pipeline_header()

        liked_result = run_liked_songs_stage()
        # recent_result = run_recent_tracks_stage()
        warehouse_result = run_warehouse_stage()
        track_metadata_result = run_track_metadata_stage()
        artist_metadata_result = run_artist_metadata_stage()
        album_art_result = run_album_art_stage()
        warehouse_enrichment_result = run_warehouse_enrichment_stage()
        analytics_result = run_analytics_stage()
        export_result = run_export_stage()

        total_runtime = perf_counter() - pipeline_start
        print_performance_summary(
            [
                ("Liked Songs", liked_result),
                #("Recent Tracks", recent_result),
                ("Warehouse", warehouse_result),
                ("Track Metadata", track_metadata_result),
                ("Artist Metadata", artist_metadata_result),
                ("Album Art", album_art_result),
                ("Warehouse Enrichment", warehouse_enrichment_result),
                ("Analytics", analytics_result),
                ("Tableau Export", export_result),
            ],
            total_runtime,
        )

    except Exception as e:
        status = "Failed"
        error_message = str(e)

        print("\nPipeline failed.")
        print(error_message)

        raise

    finally:
        runtime = perf_counter() - pipeline_start
        pipeline_end_time = datetime.now()

        log_etl_run(
            pipeline_name="Listening History ETL",
            start_time=pipeline_start_time,
            end_time=pipeline_end_time,
            runtime_seconds=runtime,
            status=status,
            liked_downloaded=liked_result.downloaded if 'liked_result' in locals() else 0,
            liked_inserted=liked_result.inserted if 'liked_result' in locals() else 0,
            recent_downloaded=recent_result.downloaded if 'recent_result' in locals() else 0,
            recent_inserted=recent_result.inserted if 'recent_result' in locals() else 0,
            error_message=error_message,
        )


# ============================================================
# Run Pipeline
# ============================================================

if __name__ == "__main__":
    main()