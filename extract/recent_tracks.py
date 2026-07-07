"""
recent_tracks.py

Author:
    Gabby Coleman

Purpose
-------
Downloads your recently played tracks from Spotify.

Spotify only provides the 50 most recent plays through the API.
By running this script on a schedule, we can build our own
complete listening history over time.

Inputs
------
Spotify Web API

Outputs
-------
data/raw/recent_tracks.csv
"""

# ============================================================
# Imports
# ============================================================

import pandas as pd

from api.spotify_client import sp


from utils.helpers import normalize_release_date

from config.settings import RECENT_TRACKS_FILE


# ============================================================
# Download Recently Played Tracks
# ============================================================

def download_recent_tracks():
    """
    Downloads your 50 most recently played tracks.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing your recent listening history.
    """

    print("Downloading recently played tracks...\n")

    results = sp.current_user_recently_played(limit=50)

    recent_tracks = []

    for item in results["items"]:

        track = item["track"]

        recent_tracks.append({

            "played_at": (
                item["played_at"]
                .replace("T", " ")
                .replace("Z", "")
            ),

            "spotify_id": track["id"],

            "spotify_uri": track["uri"],

            "track_name": track["name"],

            "artist_name": ", ".join(
                artist["name"]
                for artist in track["artists"]
            ),

            "album_name": track["album"]["name"],

            "duration_ms": track["duration_ms"]

        })

    df = pd.DataFrame(recent_tracks)

    df.to_csv(
    RECENT_TRACKS_FILE,
    index=False
)

    print(f"Downloaded {len(df)} recent tracks.")

    return df


# ============================================================
# Run this file directly
# ============================================================

if __name__ == "__main__":

    download_recent_tracks()