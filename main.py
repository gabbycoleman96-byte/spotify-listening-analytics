"""
main.py

Author:
    Gabby Coleman

Purpose
-------
Runs the complete Spotify ETL pipeline.

Pipeline
--------
1. Check for new liked songs
2. Download new liked songs
3. Load liked songs into MySQL
4. Download recent tracks
5. Refresh recent_tracks_snapshot
6. Transform recent plays into dashboard_data format
7. Load dashboard_data
8. Rebuild analytics tables
9. Export Tableau datasets
10. Log the ETL run
"""

# ============================================================
# Imports
# ============================================================

from datetime import datetime
from time import perf_counter

from extract.liked_songs import download_liked_songs
from extract.recent_tracks import download_recent_tracks

from load.database import (
    get_latest_liked_song_date,
    get_liked_song_ids
)

from load.etl_logger import log_etl_run
from load.loader import (
    load_dataframe,
    execute_sql
)

from transform.dashboard_transform import (
    build_dashboard_dataframe
)

from transform.rebuild_analytics import (
    rebuild_analytics_tables
)

from export.export_csv import export_tables

from config.pipeline import ANALYTICS_PIPELINE


# ============================================================
# Main ETL Pipeline
# ============================================================

def main():
    """Run the complete Spotify ETL pipeline."""

    pipeline_start = perf_counter()
    pipeline_start_time = datetime.now()

    status = "Success"
    error_message = None

    liked_downloaded = 0
    liked_inserted = 0

    recent_downloaded = 0
    recent_inserted = 0

    try:

        print("=" * 60)
        print("Spotify ETL Pipeline")
        print("=" * 60)

        # ====================================================
        # Liked Songs
        # ====================================================

        print("\nChecking for new liked songs...")

        latest_liked_song = get_latest_liked_song_date()

        if latest_liked_song is None:

            print("No liked songs found.")
            print("Performing full download...\n")

        else:

            print(
                f"Latest liked song: {latest_liked_song}"
            )

            print(
                "Performing incremental download...\n"
            )

        liked_df = download_liked_songs(
            stop_at=latest_liked_song
        )

        liked_downloaded = len(liked_df)

        if liked_downloaded > 0:

            liked_inserted = load_dataframe(

                liked_df,

                "liked_songs",

                ignore_duplicates=True

            )

        else:

            print("No new liked songs.")

        # ====================================================
        # Recent Tracks Snapshot
        # ====================================================

        print("\nDownloading recent tracks...")

        recent_df = download_recent_tracks()

        recent_downloaded = len(recent_df)

        print("Refreshing snapshot...")

        execute_sql("""

            TRUNCATE TABLE recent_tracks_snapshot;

        """)

        load_dataframe(

            recent_df,

            "recent_tracks_snapshot"

        )

        # ====================================================
        # Dashboard Warehouse
        # ====================================================

        print("\nBuilding dashboard dataset...")

        liked_song_ids = get_liked_song_ids()

        dashboard_df = build_dashboard_dataframe(

            recent_df,

            liked_song_ids

        )

        print("Loading dashboard_data...")

        recent_inserted = load_dataframe(

            dashboard_df,

            "dashboard_data",

            ignore_duplicates=True

        )

        # ====================================================
        # Analytics
        # ====================================================

        rebuild_analytics_tables()

        # ====================================================
        # Tableau Exports
        # ====================================================

        export_tables(

            [table for _, table in ANALYTICS_PIPELINE]

        )

        runtime = perf_counter() - pipeline_start

        print("\n")
        print("=" * 60)
        print("ETL Pipeline Summary")
        print("=" * 60)

        print("\nLiked Songs")
        print("-" * 20)
        print(f"Downloaded : {liked_downloaded:,}")
        print(f"Inserted : {liked_inserted:,}")

        print("\nRecent Plays")
        print("-" * 20)
        print(f"Downloaded : {recent_downloaded:,}")
        print(f"Inserted : {recent_inserted:,}")

        print("\nRuntime")
        print("-" * 20)
        print(f"{runtime:.2f} seconds")

        print("\nPipeline completed successfully!")

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

            pipeline_name="Spotify ETL",

            start_time=pipeline_start_time,

            end_time=pipeline_end_time,

            runtime_seconds=runtime,

            status=status,

            liked_downloaded=liked_downloaded,

            liked_inserted=liked_inserted,

            recent_downloaded=recent_downloaded,

            recent_inserted=recent_inserted,

            error_message=error_message

        )


# ============================================================
# Run Pipeline
# ============================================================

if __name__ == "__main__":

    main()
