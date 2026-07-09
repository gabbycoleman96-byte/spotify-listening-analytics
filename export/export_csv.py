"""
export_csv.py

Author:
    Gabby Coleman

Purpose
-------
Exports MySQL tables to CSV files for Tableau.

These CSVs serve as the final output of the ETL pipeline and are used
as Tableau Public data sources.
"""

# ============================================================
# Imports
# ============================================================

from pathlib import Path

import pandas as pd

from load.database import create_connection

from config.settings import EXPORT_FOLDER


# ============================================================
# Export Function
# ============================================================

def export_table(table_name):
    """
    Export a MySQL table to a CSV file.

    Parameters
    ----------
    table_name : str
        Name of the MySQL table to export.
    """

    connection = create_connection()

    try:

        query = f"SELECT * FROM {table_name}"

        df = pd.read_sql(query, connection)

        output_path = Path(EXPORT_FOLDER) / f"{table_name}.csv"

        df.to_csv(
            output_path,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"Exported {table_name} "
            f"({len(df):,} rows)"
        )

    finally:

        connection.close()


# ============================================================
# Export Multiple Tables
# ============================================================

def export_tables(table_names):
    """
    Export multiple MySQL tables.

    Parameters
    ----------
    table_names : list[str]
    """

    print("\nExporting Tableau datasets...\n")

    for table in table_names:

        export_table(table)

    print("\nAll exports complete.")
