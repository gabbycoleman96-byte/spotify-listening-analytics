"""
load_spotify_listening_warehouse.py

Author:
    Gabby Coleman

Purpose
-------
Imports Spotify Extended Streaming History JSON files,
transforms them into the spotify_listening_warehouse schema,
and loads them into MySQL.

This is intended to be run whenever a new Spotify
Streaming History export is downloaded.
"""

from time import perf_counter

from extract.import_streaming_history import import_streaming_history
from load.loader import load_dataframe


def load_spotify_listening_warehouse():
    """
    Import Spotify streaming history and load it into spotify_listening_warehouse.

    Returns
    -------
    int
        Number of rows inserted.
    """

    print("=" * 60)
    print("Loading Spotify Streaming History")
    print("=" * 60)

    start = perf_counter()

    # --------------------------------------------------------
    # Import & Transform
    # --------------------------------------------------------

    df = import_streaming_history()

    print(f"\nRows available for loading: {len(df):,}")

    # --------------------------------------------------------
    # Load into MySQL
    # --------------------------------------------------------

    inserted = load_dataframe(
        df=df,
        table_name="spotify_listening_warehouse",
        ignore_duplicates=True
    )

    runtime = perf_counter() - start

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("Spotify Listening Warehouse Load Summary")
    print("=" * 60)
    print(f"Rows processed : {len(df):,}")
    print(f"Rows inserted  : {inserted:,}")
    print(f"Rows skipped   : {len(df) - inserted:,}")
    print(f"Runtime        : {runtime:.2f} seconds")

    return inserted


if __name__ == "__main__":
    load_spotify_listening_warehouse()
