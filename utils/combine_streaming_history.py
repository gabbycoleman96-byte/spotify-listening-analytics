"""
combine_streaming_history.py

Author:
    Gabby Coleman

Purpose
-------
Combines every Spotify Extended Streaming History JSON file
into a single CSV without modifying the data.

This preserves Spotify's original export exactly as received
and creates a flat file suitable for importing into a raw
database table.
"""

from pathlib import Path
import json

import pandas as pd


# ============================================================
# Configuration
# ============================================================

INPUT_FOLDER = Path("data") / "Spotify_json_files"

OUTPUT_FILE = (
    INPUT_FOLDER
    / "listening_history_raw.csv"
)


# ============================================================
# Main
# ============================================================

def combine_streaming_history():
    """
    Combine every *.json file
    into a single CSV.
    """

    json_files = sorted(
    INPUT_FOLDER.glob("*.json")
    )

    if not json_files:
        raise FileNotFoundError(
            f"No Spotify history files found in:\n{INPUT_FOLDER}"
        )

    all_records = []

    print("\nCombining Spotify streaming history...\n")

    for file in json_files:

        print(f"Reading {file.name}")

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            records = json.load(f)

        all_records.extend(records)

    df = pd.DataFrame(all_records)

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print("\nDone!")
    print(f"Files combined : {len(json_files):,}")
    print(f"Total records  : {len(df):,}")
    print(f"Output         : {OUTPUT_FILE}")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":

    combine_streaming_history()