"""
loader.py

Author:
    Gabby Coleman

Purpose
-------
Contains reusable functions for loading Pandas DataFrames into MySQL tables
and executing SQL statements.

This module provides the primary interface for writing data to MySQL
throughout the Spotify ETL project.
"""

# ============================================================
# Imports
# ============================================================

import pandas as pd
from mysql.connector import Error

from load.database import create_connection
from pathlib import Path


# ============================================================
# Helper Functions
# ============================================================

def build_insert_query(table_name, columns, ignore_duplicates=False):
    """
    Build a parameterized INSERT statement.

    Parameters
    ----------
    table_name : str
        Destination MySQL table.

    columns : iterable
        Column names from the DataFrame.

    ignore_duplicates : bool
        If True, use INSERT IGNORE.

    Returns
    -------
    str
        SQL INSERT statement.
    """

    insert_type = (
        "INSERT IGNORE"
        if ignore_duplicates
        else "INSERT"
    )

    placeholders = ", ".join(["%s"] * len(columns))
    column_string = ", ".join(columns)

    return f"""
    {insert_type} INTO {table_name}
    ({column_string})
    VALUES ({placeholders})
    """


def dataframe_to_tuples(df):
    """
    Convert a DataFrame into tuples that MySQL understands.

    Any Pandas NaN values become Python None values so MySQL stores
    them as NULL.
    """

    clean_df = df.astype(object).where(pd.notna(df), None)

    return [tuple(row) for row in clean_df.to_numpy()]


# ============================================================
# SQL Execution
# ============================================================

def execute_sql(query):
    """
    Execute a SQL statement.

    Intended for SQL operations that do not involve loading a
    Pandas DataFrame, such as:

    - INSERT ... SELECT
    - DELETE
    - TRUNCATE
    - UPDATE
    - CREATE TABLE

    Parameters
    ----------
    query : str
        SQL statement to execute.

    Returns
    -------
    int
        Number of affected rows (when available).
    """

    connection = None
    cursor = None

    try:

        connection = create_connection()
        cursor = connection.cursor()

        cursor.execute(query)

        connection.commit()

        print("SQL statement executed successfully.")

        return cursor.rowcount

    except Error as e:

        if connection:
            connection.rollback()

        print(f"\nDatabase Error:\n{e}")

        return 0

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

            print("Database connection closed.")


def execute_sql_file(file_path):
    """
    Execute every SQL statement contained in a .sql file.

    Parameters
    ----------
    file_path : str or Path
        Path to the SQL script.
    """

    connection = None
    cursor = None

    try:

        connection = create_connection()
        cursor = connection.cursor()

        sql = Path(file_path).read_text(
            encoding="utf-8"
        )

        for statement in sql.split(";"):

            statement = statement.strip()

            if statement:

                cursor.execute(statement)

        connection.commit()

        print(
            f"Executed SQL file: {Path(file_path).name}"
        )

    except Error as e:

        if connection:
            connection.rollback()

        print(f"\nDatabase Error:\n{e}")

        raise

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

# ============================================================
# Main DataFrame Loader
# ============================================================

def load_dataframe(
    df,
    table_name,
    ignore_duplicates=False,
    batch_size=1000
):
    """
    Load a DataFrame into a MySQL table.

    Parameters
    ----------
    df : pandas.DataFrame
        Data to load.

    table_name : str
        Destination MySQL table.

    ignore_duplicates : bool, optional
        Ignore duplicate primary keys.

    batch_size : int, optional
        Number of rows per batch.

    Returns
    -------
    int
        Total number of inserted rows.
    """

    connection = None
    cursor = None

    try:

        connection = create_connection()
        cursor = connection.cursor()

        query = build_insert_query(
            table_name,
            df.columns,
            ignore_duplicates
        )

        data = dataframe_to_tuples(df)

        rows_inserted = 0

        for start in range(0, len(data), batch_size):

            batch = data[start:start + batch_size]

            cursor.executemany(query, batch)

            connection.commit()

            rows_inserted += cursor.rowcount

            print(
                f"Processed rows "
                f"{start + 1:,}"
                f" - "
                f"{min(start + batch_size, len(data)):,}"
            )

        print(
            f"\nSuccessfully inserted "
            f"{rows_inserted:,} rows into '{table_name}'."
        )

        return rows_inserted

    except Error as e:

        if connection:
            connection.rollback()

        print(f"\nDatabase Error:\n{e}")

        return 0

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

            print("Database connection closed.")