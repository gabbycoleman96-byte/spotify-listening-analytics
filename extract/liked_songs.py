"""
liked_songs.py

Author:
    Gabby Coleman

Purpose
-------
Download the user's Spotify liked songs.

This extractor can perform either:

• A full download
• An incremental download that stops once a specified
  "added_to_library" timestamp is reached.

The extractor does NOT know anything about MySQL.
It simply returns a DataFrame.
"""

# ============================================================
# Imports
# ============================================================

import os
from datetime import datetime

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

from config.settings import LIKED_SONGS_FILE
from utils.helpers import normalize_release_date

# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# Spotify Client
# ============================================================

scope = "user-library-read"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=scope
    )
)


# ============================================================
# Extract Liked Songs
# ============================================================

def download_liked_songs(stop_at=None):
    """
    Download liked songs from Spotify.

    Parameters
    ----------
    stop_at : datetime.datetime, optional

        If provided, downloading stops once songs already
        present in the database are reached.

    Returns
    -------
    pandas.DataFrame
    """

    print("Downloading liked songs...\n")

    tracks = []

    results = sp.current_user_saved_tracks(limit=50)

    while results:

        for item in results["items"]:

            added_timestamp = datetime.strptime(
                item["added_at"],
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # --------------------------------------------------
            # Incremental download
            # --------------------------------------------------

            if stop_at is not None:

                if added_timestamp <= stop_at:

                    print(
                        "Reached previously downloaded songs."
                    )

                    df = pd.DataFrame(tracks)

                    df.to_csv(
                        LIKED_SONGS_FILE,
                        index=False
                    )

                    print(
                        f"\nDownloaded {len(df)} new liked songs."
                    )

                    return df

            track = item["track"]

            tracks.append({

                    "spotify_id": track["id"],

                    "spotify_uri": track["uri"],

                    "track_name": track["name"],

                    "artist_name": ", ".join(
                        artist["name"]
                        for artist in track["artists"]
                    ),

                    "album_name": track["album"]["name"],

                    "release_date": normalize_release_date(
                        track["album"]["release_date"]
                    ),

                    "added_to_library": added_timestamp,

                    "duration_ms": track["duration_ms"],

                    "popularity": track.get("popularity")

            })

        if results["next"]:

            results = sp.next(results)

        else:

            break

    df = pd.DataFrame(tracks)

    df.to_csv(
        LIKED_SONGS_FILE,
        index=False
    )

    print(
        f"\nDownloaded {len(df)} liked songs."
    )

    return df


# ============================================================
# Run directly
# ============================================================

if __name__ == "__main__":

    download_liked_songs()