
"""
import_streaming_history.py

Reads every Spotify Extended Streaming History JSON file, combines them,
standardizes the schema, removes duplicates, and returns a warehouse-ready
DataFrame for spotify_listening_warehouse.
"""

from pathlib import Path
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FOLDER = PROJECT_ROOT / "Spotify_json_files"

def _load_json_file(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def import_streaming_history(folder=DEFAULT_FOLDER):
    folder = Path(folder)
    json_files = sorted(folder.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {folder}")

    frames = []
    for file in json_files:
        print(f"Reading {file.name}")
        frames.append(pd.DataFrame(_load_json_file(file)))

    df = pd.concat(frames, ignore_index=True)
    df = df[df["spotify_track_uri"].notna()].copy()

    df.rename(columns={
        "ts":"played_at",
        "master_metadata_track_name":"track_name",
        "master_metadata_album_artist_name":"artist_name",
        "master_metadata_album_album_name":"album_name",
        "spotify_track_uri":"spotify_uri",
        "shuffle":"shuffle_state"
    }, inplace=True)

    df["played_at"] = pd.to_datetime(df["played_at"], utc=True).dt.tz_convert(None)
    df["spotify_id"] = df["spotify_uri"].str.replace("spotify:track:","",regex=False)

    df["date"] = df["played_at"].dt.date
    df["year"] = df["played_at"].dt.year
    df["quarter"] = df["played_at"].dt.quarter
    df["month_number"] = df["played_at"].dt.month
    df["month_name"] = df["played_at"].dt.month_name()
    df["week"] = df["played_at"].dt.isocalendar().week.astype(int)
    df["day"] = df["played_at"].dt.day
    df["weekday_number"] = df["played_at"].dt.weekday + 1
    df["weekday_name"] = df["played_at"].dt.day_name()
    df["hour"] = df["played_at"].dt.hour
    df["hour_label"] = df["played_at"].dt.strftime("%I %p").str.lstrip("0")
    df["time"] = df["played_at"].dt.time

    df["duration_ms"] = None
    df["is_liked"] = False
    df["primary_genre"] = None
    df["secondary_genre"] = None
    df["album_art_url"] = None
    df["dominant_color"] = None
    df["source"] = "Spotify Export"
    df["imported_at"] = pd.Timestamp.now()

    cols = [
        "played_at","date","year","quarter","month_number","month_name","week","day",
        "weekday_number","weekday_name","hour","hour_label","time","ms_played",
        "duration_ms","shuffle_state","skipped","track_name","artist_name","album_name",
        "spotify_id","spotify_uri","is_liked","primary_genre","secondary_genre",
        "album_art_url","dominant_color","source","imported_at"
    ]

    df = df[cols].drop_duplicates(subset=["played_at","spotify_id"])

    print(f"Final dataset: {len(df):,} rows")
    return df

if __name__ == "__main__":
    df = import_streaming_history()
    print(df.head())
