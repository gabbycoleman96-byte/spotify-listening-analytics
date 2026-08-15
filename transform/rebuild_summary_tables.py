"""
rebuild_summary_tables.py

Author:
    Gabby Coleman

Purpose
-------
Rebuilds every summary table used by Tableau.
"""

from pathlib import Path

from load.loader import execute_sql_file

ANALYSIS_FOLDER = Path("sql") / "analysis"


def rebuild_analytics_tables():
    """
    Execute every analytics SQL script.
    """

    sql_files = sorted(ANALYSIS_FOLDER.glob("*.sql"))

    for sql_file in sql_files:
        print(f"  • {sql_file.name}")
        execute_sql_file(sql_file)

    print("\nAnalytics tables rebuilt successfully.")