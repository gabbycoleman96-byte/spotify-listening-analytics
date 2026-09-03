"""
load_track_metadata.py

Author
------
Gabby Coleman

Purpose
-------
Downloads metadata for Spotify tracks that do not already exist
in the track_metadata table and loads them into MySQL.

This module is responsible for the entire metadata ETL stage:

    Warehouse
        ↓
Find missing Spotify IDs
        ↓
Download metadata from Spotify
        ↓
Load into track_metadata
"""

# ============================================================
# Imports
# ============================================================

import time

import pandas as pd

from spotipy.exceptions import SpotifyException

from api.spotify_client import sp
from load.loader import fetch_dataframe
from load.loader import load_dataframe
from datetime import datetime, UTC


# ============================================================
# Constants
# ============================================================

MAX_RATE_LIMIT_WAIT = 3600  # 1 hour


# ============================================================
# Find Missing Track IDs
# ============================================================

def get_missing_track_uris():
    """
    Return canonical Spotify track URIs that do not yet
    exist in track_metadata.
    """

    query = """
        SELECT
            c.canonical_uri,
            COUNT(*) AS play_count

        FROM canonical_song_uris c

        JOIN listening_history_warehouse h
            ON h.spotify_id = c.spotify_id

        LEFT JOIN track_metadata t
            ON t.spotify_uri = c.canonical_uri

        WHERE t.spotify_id IS NULL

        GROUP BY c.canonical_uri

        ORDER BY play_count DESC

        LIMIT 600;
    """

    df = fetch_dataframe(query)

    return df["canonical_uri"].tolist()


# ============================================================
# Download Metadata
# ============================================================

def download_track_metadata(track_ids):
    """
    Download metadata for Spotify tracks.

    Parameters
    ----------
    track_ids : list[str]

    Returns
    -------
    dict[str, pandas.DataFrame]
    """

    if not track_ids:
        return {
            "tracks": pd.DataFrame(),
            "albums": pd.DataFrame(),
            "artists": pd.DataFrame(),
            "track_artists": pd.DataFrame(),
        }

    track_records = []
    album_records = {}
    artist_records = {}
    track_artist_records = []
    scraped_at = datetime.now(UTC)

    total_tracks = len(track_ids)
    
    quota_exhausted = False

    print(
        f"\nDownloading metadata for "
        f"{total_tracks:,} tracks..."
    )

    for index, track_id in enumerate(
        track_ids,
        start=1,
    ):

        if index == 1 or index % 100 == 0:

            print(
                f"Track {index:,} of {total_tracks:,}"
            )

        while True:

            try:

                track = sp.track(track_id)

                break

            except SpotifyException as e:

                if e.http_status == 429:

                    print("\nSpotify metadata quota reached.")
                    print("Stopping metadata downloads.")
                    print("Continuing with the rest of the ETL pipeline...")

                    quota_exhausted = True

                    track = None

                    break


            except Exception as e:

                print(
                    f"Skipping {track_id}: {e}"
                )

                track = None

                break

        if quota_exhausted:
            break

        if track is None:
            continue

        album = track["album"]

        artists = track.get("artists", [])

        primary_artist = artists[0] if artists else {}

        album_id = album.get("id")
        album_art_url = None
        images = album.get("images", [])

        if images:
            largest_image = max(
                images,
                key=lambda img: img.get("height", 0),
                default=None,
            )

            album_art_url = (
                largest_image["url"]
                if largest_image
                else None
            )

        track_records.append(
            {
                "spotify_id": track.get("id"),
                "spotify_uri": track.get("uri"),
                "track_name": track.get("name"),
                "primary_artist_id": primary_artist.get("id"),
                "album_id": album_id,
                "duration_ms": track.get("duration_ms"),
                "popularity": track.get("popularity"),
                "explicit": track.get("explicit"),
                "is_local": track.get("is_local"),
                "is_playable": track.get("is_playable", True),
                "track_number": track.get("track_number"),
                "disc_number": track.get("disc_number"),
                "preview_url": track.get("preview_url"),
                "isrc": track.get("external_ids", {}).get("isrc"),
                "spotify_url": track.get("external_urls", {}).get("spotify"),
                "scraped_at": scraped_at,
            }
        )

        if album_id:
            album_records[album_id] = {
                "album_id": album_id,
                "album_uri": album.get("uri"),
                "album_name": album.get("name"),
                "album_type": album.get("album_type"),
                "release_date": album.get("release_date"),
                "release_date_precision": album.get("release_date_precision"),
                "total_tracks": album.get("total_tracks"),
                "album_art_url": album_art_url,
                "label": None,
                "spotify_url": album.get("external_urls", {}).get("spotify"),
                "scraped_at": scraped_at,
            }

        for artist_order, artist in enumerate(artists, start=1):

            artist_id = artist.get("id")

            if artist_id:
                artist_records[artist_id] = {
                    "artist_id": artist_id,
                    "artist_uri": artist.get("uri"),
                    "artist_name": artist.get("name"),
                    "spotify_url": artist.get("external_urls", {}).get("spotify"),
                    "popularity": None,
                    "followers": None,
                    "genres": None,
                    "image_url": None,
                    "scraped_at": scraped_at,
                }

            if artist_id:
                track_artist_records.append(
                    {
                        "spotify_id": track.get("id"),
                        "artist_id": artist_id,
                        "artist_order": artist_order,
                    }
                )

        # Small delay to reduce the chance of hitting
        # Spotify's rate limits during the initial
        # metadata bootstrap.
        time.sleep(0.05)

    tracks_df = pd.DataFrame(track_records)
    albums_df = pd.DataFrame(album_records.values())
    artists_df = pd.DataFrame(artist_records.values())
    track_artists_df = pd.DataFrame(track_artist_records)

    print(
        "\nDownloaded metadata:"
        f"\n  Tracks:         {len(tracks_df):,}"
        f"\n  Albums:         {len(albums_df):,}"
        f"\n  Artists:        {len(artists_df):,}"
        f"\n  Track Artists:  {len(track_artists_df):,}"
    )

    return {
        "tracks": tracks_df,
        "albums": albums_df,
        "artists": artists_df,
        "track_artists": track_artists_df,
    }


# ============================================================
# Main Loader
# ============================================================

def load_track_metadata():
    """
    Download and load metadata for tracks missing
    from the track_metadata table.

    Returns
    -------
    dict[str, pandas.DataFrame]
    """

    missing_track_uris = get_missing_track_uris()

    if not missing_track_uris:

        print(
            "\nTrack metadata is already up to date."
        )

        return {
            "tracks": pd.DataFrame(),
            "albums": pd.DataFrame(),
            "artists": pd.DataFrame(),
            "track_artists": pd.DataFrame(),
        }

    print(
        f"\nFound "
        f"{len(missing_track_uris):,} "
        f"tracks missing metadata."
    )

    metadata = download_track_metadata(
        missing_track_uris
    )

    if metadata["tracks"].empty:

        print(
            "\nNo metadata was downloaded."
        )

        return metadata
    
    load_dataframe(
        metadata["albums"],
        "album_metadata",
        ignore_duplicates=True,
    )

    load_dataframe(
        metadata["artists"],
        "artist_metadata",
        ignore_duplicates=True,
    )

    load_dataframe(
        metadata["tracks"],
        "track_metadata",
        ignore_duplicates=True,
    )

    load_dataframe(
        metadata["track_artists"],
        "track_artists",
        ignore_duplicates=True,
    )

    print(
        "\nLoaded metadata:"
        f"\n  Tracks:         {len(metadata['tracks']):,}"
        f"\n  Albums:         {len(metadata['albums']):,}"
        f"\n  Artists:        {len(metadata['artists']):,}"
        f"\n  Track Artists:  {len(metadata['track_artists']):,}"
    )

    return metadata