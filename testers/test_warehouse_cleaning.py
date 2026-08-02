"""
test_warehouse_cleaning.py

Runs the warehouse cleaning pipeline against the raw Spotify table
without rebuilding the warehouse.
"""

from load.reader import read_table
from transform.warehouse_cleaning import clean_warehouse


def main():

    print("=" * 60)
    print("Spotify Warehouse Cleaning Test")
    print("=" * 60)

    print("\nLoading raw Spotify history...")

    df = read_table("spotify_streaming_history_raw")

    print(f"Loaded {len(df):,} rows.")

    cleaned_df = clean_warehouse(df)

    print("\nCleaning complete.\n")

    print(f"Original rows : {len(df):,}")
    print(f"Clean rows    : {len(cleaned_df):,}")
    print(f"Rows removed  : {len(df) - len(cleaned_df):,}")


if __name__ == "__main__":
    main()
    

print("\nNo changes were written to MySQL.")
print("This script is for testing only.")