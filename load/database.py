"""
database.py

Author:
    Gabby Coleman

Purpose
-------
Creates and manages a reusable connection to the MySQL database.

Why do we have this file?
-------------------------
Instead of every Python script creating its own database connection,
every script will simply import the create_connection() function.

Example
-------
from load.database import create_connection

connection = create_connection()

Benefits
--------
✓ Only one place to update credentials
✓ Easier debugging
✓ Cleaner code
✓ Follows the DRY (Don't Repeat Yourself) principle
"""

# ============================================================
# Imports
# ============================================================

import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# ============================================================
# Locate the project root folder
# ============================================================
#
# __file__ points to this file:
#
# spotify_etl/load/database.py
#
# .parent           = load/
# .parent.parent    = spotify_etl/
#
# This allows us to ALWAYS find the project's root folder,
# no matter which script is running.
#

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# Locate the .env file
# ============================================================

ENV_FILE = PROJECT_ROOT / ".env"

print(f"Loading environment file from:\n{ENV_FILE}\n")

load_dotenv(dotenv_path=ENV_FILE)


# ============================================================
# Verify required environment variables exist
# ============================================================

REQUIRED_VARIABLES = [

    "MYSQL_HOST",

    "MYSQL_PORT",

    "MYSQL_DATABASE",

    "MYSQL_USER",

    "MYSQL_PASSWORD"

]

for variable in REQUIRED_VARIABLES:

    if os.getenv(variable) is None:

        raise ValueError(

            f"""
Environment variable '{variable}' was not found.

Please check your .env file.

Expected location:

{ENV_FILE}
"""
        )


# ============================================================
# Create MySQL Connection
# ============================================================

def create_connection():
    """
    Creates a connection to the MySQL database.

    Returns
    -------
    mysql.connector.connection.MySQLConnection
    """

    connection = mysql.connector.connect(

        host=os.getenv("MYSQL_HOST"),

        port=int(os.getenv("MYSQL_PORT")),

        database=os.getenv("MYSQL_DATABASE"),

        user=os.getenv("MYSQL_USER"),

        password=os.getenv("MYSQL_PASSWORD")

    )

    return connection


def get_latest_liked_song_date():
    """
    Return the newest added_to_library timestamp currently stored
    in the liked_songs table.

    Returns
    -------
    datetime.datetime | None
        Latest timestamp, or None if the table is empty.
    """

    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT MAX(added_to_library)
        FROM liked_songs
    """)

    latest_date = cursor.fetchone()[0]

    cursor.close()
    connection.close()

    return latest_date


# ============================================================
# Test the connection
# ============================================================

if __name__ == "__main__":

    print("Connecting to MySQL...\n")

    connection = create_connection()

    print("✅ Connected Successfully!")

    print(f"Database: {connection.database}")

    connection.close()

    print("Connection closed.")