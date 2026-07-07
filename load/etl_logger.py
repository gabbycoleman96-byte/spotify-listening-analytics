"""
etl_logger.py

Utility functions for recording ETL pipeline runs.
"""

from load.database import create_connection


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
    error_message=None
):
    """
    Record one ETL pipeline execution.
    """

    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
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
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
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
    )

    connection.commit()

    cursor.close()
    connection.close()