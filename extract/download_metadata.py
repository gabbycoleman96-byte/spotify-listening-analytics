"""
download_metadata.py

Purpose
-------
Downloads track metadata from the Spotify Web API.

This module only communicates with Spotify.

It does NOT write to MySQL or perform any warehouse logic.
Instead, it returns clean pandas DataFrames that can be loaded
by the ETL pipeline.
"""

from math import ceil

import pandas as pd

from api.spotify_client import sp


# --------------------------------------------------
# Download metadata for a list of Spotify track IDs
# --------------------------------------------------

def download_track_metadata(track_ids):
    """
    Download metadata for one or more Spotify tracks.

    Parameters
    ----------
    track_ids : list[str]
        List of Spotify track IDs.

    Returns
    -------
    pandas.DataFrame
        One row per track.
    """

    if not track_ids:
        return pd.DataFrame()

    records = []

    batch_size = 50
    total_batches = ceil(len(track_ids) / batch_size)

    print(f"\nDownloading metadata for {len(track_ids):,} tracks...")

    for batch_number, start in enumerate(
        range(0, len(track_ids), batch_size),
        start=1,
    ):

        end = start + batch_size

        batch = track_ids[start:end]

        print(
            f"Batch {batch_number:,} of {total_batches:,}"
        )

        response = sp.tracks(batch)

        for track in response["tracks"]:

            if track is None:
                continue

            album = track["album"]

            artists = track["artists"]

            artist = artists[0] if artists else {}

            images = album.get("images", [])

            album_art_url = (
                images[0]["url"]
                if images
                else None
            )

            records.append(
                {
                    "spotify_id": track["id"],
                    "track_name": track["name"],
                    "artist_id": artist.get("id"),
                    "artist_name": artist.get("name"),
                    "album_name": album["name"],
                    "duration_ms": track["duration_ms"],
                    "release_date": album["release_date"],
                    "album_art_url": album_art_url,
                }
            )

    df = pd.DataFrame(records)

    print(
        f"Downloaded metadata for {len(df):,} tracks."
    )

    return df