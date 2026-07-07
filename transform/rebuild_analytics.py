"""
rebuild_analytics.py

Author:
    Gabby Coleman

Purpose
-------
Rebuilds every analytics table used by Tableau.
"""

from pathlib import Path

from load.loader import execute_sql_file
from config.pipeline import ANALYTICS_PIPELINE


ANALYSIS_FOLDER = Path("sql") / "analysis"


def rebuild_analytics_tables():
    """
    Execute every analytics SQL script.
    """

    print("\nRebuilding analytics tables...\n")

    for sql_file, _ in ANALYTICS_PIPELINE:

        execute_sql_file(
            ANALYSIS_FOLDER / sql_file
        )

    print("\nAnalytics tables rebuilt successfully.")