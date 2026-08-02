"""
reader.py

Author:
    Gabby Coleman

Purpose
-------
Reusable functions for reading data from the database
into Pandas DataFrames.

All database access uses the project's shared SQLAlchemy
engine defined in load.database.
"""

# ============================================================
# Imports
# ============================================================

import pandas as pd
from sqlalchemy import text

from load.database import engine


# ============================================================
# Data Readers
# ============================================================

def read_table(table_name):
    """
    Load an entire database table into a Pandas DataFrame.

    Parameters
    ----------
    table_name : str
        Name of the table to read.

    Returns
    -------
    pandas.DataFrame
    """

    query = text(f"""
        SELECT *
        FROM {table_name}
    """)

    return pd.read_sql(query, engine)

def read_query(query):
    """
    Execute a SELECT query and return the results
    as a Pandas DataFrame.

    Parameters
    ----------
    query : str | sqlalchemy.sql.elements.TextClause

    Returns
    -------
    pandas.DataFrame
    """

    if isinstance(query, str):
        query = text(query)

    return pd.read_sql(query, engine)