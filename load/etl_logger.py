"""
etl_logger.py

Author:
    Gabby Coleman

Purpose
-------
Utility functions for recording ETL pipeline runs.
"""

# ============================================================
# Imports
# ============================================================

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from load.database import engine


# ============================================================
# ETL Logging
# ============================================================

def log_etl_run(
    pipeline_name,
    start_time,
    end_time,
    runtime_seconds,
    status,
    liked_downloaded,
    liked_inserted,
    recent_downloaded,
    recent_inserted,
    error_message=None,
):
    """
    Record one ETL pipeline execution.
    """

    query = text("""
        INSERT INTO etl_log
        (
            pipeline_name,
            start_time,
            end_time,
            runtime_seconds,
            status,
            liked_downloaded,
            liked_inserted,
            recent_downloaded,
            recent_inserted,
            error_message
        )
        VALUES
        (
            :pipeline_name,
            :start_time,
            :end_time,
            :runtime_seconds,
            :status,
            :liked_downloaded,
            :liked_inserted,
            :recent_downloaded,
            :recent_inserted,
            :error_message
        )
    """)

    try:

        with engine.begin() as connection:

            connection.execute(
                query,
                {
                    "pipeline_name": pipeline_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "runtime_seconds": runtime_seconds,
                    "status": status,
                    "liked_downloaded": liked_downloaded,
                    "liked_inserted": liked_inserted,
                    "recent_downloaded": recent_downloaded,
                    "recent_inserted": recent_inserted,
                    "error_message": error_message,
                },
            )

    except SQLAlchemyError as e:

        print(f"\nWarning: Unable to write ETL log.\n{e}")

        # Never let logging failures crash the ETL.
        raise