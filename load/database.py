"""
database.py

Author:
    Gabby Coleman

Purpose
-------
Creates and manages the project's SQLAlchemy engine.

Why SQLAlchemy?
---------------
Instead of every module creating and closing its own MySQL connection,
the entire project shares one SQLAlchemy Engine.

Benefits
--------
✓ One connection pool for the entire project
✓ No more pandas SQL warnings
✓ Cleaner code
✓ Faster repeated database operations
✓ Easier future migration to PostgreSQL or SQLite
✓ Centralized database configuration

Example
-------
from load.database import engine

df = pd.read_sql(
    "SELECT * FROM liked_songs",
    engine
)
"""

# ============================================================
# Imports
# ============================================================

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ============================================================
# Project Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / ".env"

print(f"Loading environment file from:\n{ENV_FILE}\n")

load_dotenv(dotenv_path=ENV_FILE)

# ============================================================
# Validate Environment Variables
# ============================================================

REQUIRED_VARIABLES = [

    "MYSQL_HOST",

    "MYSQL_PORT",

    "MYSQL_DATABASE",

    "MYSQL_USER",

    "MYSQL_PASSWORD"

]

for variable in REQUIRED_VARIABLES:

    if not os.getenv(variable):

        raise ValueError(
            f"""
Environment variable '{variable}' was not found.

Please check your .env file.

Expected location:

{ENV_FILE}
"""
        )

# ============================================================
# Database Configuration
# ============================================================

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

DATABASE_URL = (
    f"mysql+mysqlconnector://"
    f"{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}"
    f"/{MYSQL_DATABASE}"
)

# ============================================================
# Shared SQLAlchemy Engine
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)

# ============================================================
# Helper Functions
# ============================================================

def get_latest_liked_song_date():
    """
    Return the newest liked song timestamp.
    """

    query = text("""
        SELECT MAX(added_to_library)
        FROM liked_songs
    """)

    with engine.connect() as connection:

        return connection.execute(query).scalar()


def get_liked_song_ids():
    """
    Return every liked Spotify track ID.

    Returns
    -------
    set[str]
    """

    query = text("""
        SELECT spotify_id
        FROM liked_songs
    """)

    with engine.connect() as connection:

        rows = connection.execute(query)

        return {

            row.spotify_id

            for row in rows

            if row.spotify_id

        }


# ============================================================
# Test Connection
# ============================================================

if __name__ == "__main__":

    print("Testing database connection...\n")

    with engine.connect() as connection:

        database_name = connection.execute(
            text("SELECT DATABASE();")
        ).scalar()

    print("✅ Connected Successfully!")
    print(f"Database: {database_name}")