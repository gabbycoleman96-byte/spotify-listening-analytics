"""
loader.py

Author:
    Gabby Coleman

Purpose
-------
Contains reusable functions for loading Pandas DataFrames into MySQL tables
and executing SQL statements.

All database writes use the project's shared SQLAlchemy engine.
"""

# ============================================================
# Imports
# ============================================================

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from tqdm import tqdm

from config.warehouse_schema import SOURCE_COLUMNS
from load.database import engine


# ============================================================
# Helper Functions
# ============================================================

def build_insert_query(
    table_name,
    columns,
    ignore_duplicates=False
):
    """
    Build a parameterized INSERT statement.

    Parameters
    ----------
    table_name : str
        Destination table.

    columns : iterable
        DataFrame column names.

    ignore_duplicates : bool
        If True, uses INSERT IGNORE.

    Returns
    -------
    sqlalchemy.sql.elements.TextClause
    """

    insert_type = (
        "INSERT IGNORE"
        if ignore_duplicates
        else "INSERT"
    )

    placeholders = ", ".join(
        f":{column}"
        for column in columns
    )

    column_string = ", ".join(columns)

    return text(f"""
        {insert_type} INTO {table_name}
        ({column_string})
        VALUES ({placeholders})
    """)


def dataframe_to_records(df):
    """
    Convert a DataFrame into dictionaries suitable for SQLAlchemy.

    NaN values become None so MySQL stores NULL.
    """

    clean_df = (
        df.astype(object)
        .where(pd.notna(df), None)
    )

    return clean_df.to_dict(
        orient="records"
    )


# ============================================================
# SQL Execution
# ============================================================

def execute_sql(query, params=None):
    """
    Execute a SQL statement.

    Parameters
    ----------
    query : str
    params : dict | None
        Parameters for the SQL statement.

    Returns
    -------
    int
        Number of affected rows.
    """

    try:

        with engine.begin() as connection:

            result = connection.execute(
                text(query),
                params or {}
            )


        return result.rowcount

    except SQLAlchemyError as e:

        print(f"\nDatabase Error:\n{e}")

        raise


def execute_sql_file(file_path):
    """
    Execute every SQL statement contained in a .sql file.

    Parameters
    ----------
    file_path : str | Path
    """

    sql = Path(file_path).read_text(
        encoding="utf-8"
    )

    try:

        with engine.begin() as connection:

            for statement in sql.split(";"):

                statement = statement.strip()

                if not statement:
                    continue

                result = connection.execute(
                    text(statement)
                )

                if result.returns_rows:
                    result.fetchall()

        print(
            f"Executed SQL file: {Path(file_path).name}"
        )

    except SQLAlchemyError as e:

        print(f"\nDatabase Error:\n{e}")

        raise
    
# ============================================================
# Main DataFrame Loader
# ============================================================

def load_dataframe(
    df,
    table_name,
    ignore_duplicates=False,
    batch_size=8000,
):
    """
    Load a DataFrame into a MySQL table.

    Parameters
    ----------
    df : pandas.DataFrame
        Data to load.

    table_name : str
        Destination table.

    ignore_duplicates : bool, default False
        Use INSERT IGNORE.

    batch_size : int, default 8000
        Number of rows per batch.

    Returns
    -------
    int
        Number of inserted rows.
    """

    if df.empty:

        print(f"No rows to load into '{table_name}'.")

        return 0

    query = build_insert_query(
        table_name=table_name,
        columns=df.columns,
        ignore_duplicates=ignore_duplicates,
    )

    data = dataframe_to_records(df)

    rows_inserted = 0

    try:

        with engine.begin() as connection:

            with tqdm(
                total=len(data),
                desc=f"Loading {table_name}",
                unit="rows",
                unit_scale=True,
                dynamic_ncols=True,
            ) as pbar:

                for start in range(0, len(data), batch_size):

                    batch = data[start:start + batch_size]

                    result = connection.execute(
                        query,
                        batch,
                    )

                    if result.rowcount is not None:

                        rows_inserted += result.rowcount

                    pbar.update(len(batch))

        print(
            f"\nSuccessfully inserted "
            f"{rows_inserted:,} rows into '{table_name}'."
        )

        return rows_inserted

    except SQLAlchemyError as e:

        print(f"\nDatabase Error:\n{e}")

        raise
    
def fetch_dataframe(query):
    """
    Execute a SELECT statement and return the results
    as a pandas DataFrame.
    """

    try:

        with engine.begin() as connection:

            return pd.read_sql(
                text(query),
                connection,
            )

    except SQLAlchemyError as e:

        print(f"\nDatabase Error:\n{e}")

        raise