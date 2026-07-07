import pandas as pd

from load.loader import load_dataframe
from config.settings import LIKED_SONGS_FILE

print("Reading liked songs from CSV...")

df = pd.read_csv(LIKED_SONGS_FILE)


print(f"Loaded {len(df):,} songs from CSV.")

print("\nLoading data into MySQL...")

rows_inserted = load_dataframe(df, "liked_songs")

print(f"\nInserted {rows_inserted:,} rows.")