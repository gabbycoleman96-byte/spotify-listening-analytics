"""
load_listening_history_raw.py

Loads the combined Spotify Extended Streaming History CSV
into listening_history_raw.
"""

from pathlib import Path

import pandas as pd

from load.loader import load_dataframe


CSV_FILE = Path("data") / "Spotify_json_files" / "listening_history_raw.csv"

TABLE_NAME = "listening_history_raw"


def load_listening_history_raw():
    print("\nLoading raw Spotify listening history...\n")
    

    df = pd.read_csv(
        CSV_FILE,
        low_memory=False,
        keep_default_na=True,
    )

    df["source"] = "Spotify Export"

    # Convert timestamps to MySQL DATETIME format
    df["ts"] = pd.to_datetime(df["ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Replace pandas NaN with Python None so MySQL inserts NULL
    df = df.where(pd.notna(df), None)

    inserted = load_dataframe(df, TABLE_NAME)

    print(f"\nInserted {inserted:,} rows into {TABLE_NAME}.")


if __name__ == "__main__":
    load_listening_history_raw()