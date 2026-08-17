"""
load_artist_metadata.py

Downloads metadata for Spotify artists that do not yet have
complete metadata and updates the artist_metadata table.
"""

import time
from datetime import datetime, UTC

import pandas as pd
from spotipy.exceptions import SpotifyException

from api.spotify_client import sp
from load.loader import fetch_dataframe, execute_sql


MAX_ARTIST_REQUESTS = 600


# ============================================================
# Find Artists Needing Metadata
# ============================================================

def get_missing_artist_ids():
    """
    Return artist IDs that exist in track_artists but do not
    yet have complete artist metadata.
    """

    query = """
        SELECT DISTINCT
            ta.artist_id
        FROM track_artists ta
        LEFT JOIN artist_metadata a
            ON ta.artist_id = a.artist_id
        WHERE
            ta.artist_id IS NOT NULL
            AND (
                a.artist_id IS NULL
                OR a.scraped_at IS NULL
            )
        ORDER BY
            ta.artist_id
        LIMIT 600;
        """

    df = fetch_dataframe(query)

    return df["artist_id"].tolist()


# ============================================================
# Download Artist Metadata
# ============================================================

def download_artist_metadata(artist_ids):
    """
    Download metadata for Spotify artists.

    Uses one Spotify API request per artist because the
    multi-artist endpoint is no longer available.
    """

    if not artist_ids:
        return pd.DataFrame()

    records = []
    scraped_at = datetime.now(UTC)

    total_artists = len(artist_ids)

    print(
        f"\nDownloading metadata for "
        f"{total_artists:,} artists..."
    )
    
    quota_exhausted = False

    for index, artist_id in enumerate(
        artist_ids,
        start=1,
    ):

        if index == 1 or index % 100 == 0:

            print(
                f"Artist {index:,} of "
                f"{total_artists:,}"
            )

        while True:

            try:

                artist = sp.artist(artist_id)

                break

            except SpotifyException as e:

                if e.http_status == 429:

                    print("\nSpotify artist metadata quota reached.")
                    print("Stopping artist metadata downloads.")
                    print("Continuing with the rest of the ETL pipeline...")

                    quota_exhausted = True
                    artist = None

                    break

                else:

                    print(
                        f"Skipping artist {artist_id}: {e}"
                    )

                    artist = None

                    break

            except Exception as e:

                print(
                    f"Skipping artist {artist_id}: {e}"
                )

                artist = None

                break
            
        if quota_exhausted:
            break

        if artist is None:
            continue

        images = artist.get("images", [])

        image_url = None

        if images:

            largest_image = max(
                images,
                key=lambda img: img.get("height", 0),
                default=None,
            )

            if largest_image:
                image_url = largest_image.get("url")

        records.append(
            {
                "artist_id": artist.get("id"),
                "artist_uri": artist.get("uri"),
                "artist_name": artist.get("name"),
                "popularity": artist.get("popularity"),
                "followers": (
                    artist.get("followers", {})
                    .get("total")
                ),
                "genres": artist.get("genres"),
                "image_url": image_url,
                "spotify_url": (
                    artist.get("external_urls", {})
                    .get("spotify")
                ),
                "scraped_at": scraped_at,
            }
        )

        time.sleep(0.05)

    df = pd.DataFrame(records)

    print(
        "\nDownloaded artist metadata:"
        f"\n  Artists: {len(df):,}"
    )

    return df


# ============================================================
# Update Artist Metadata
# ============================================================

def update_artist_metadata(df):
    """
    Update existing artist_metadata rows with downloaded
    Spotify metadata.
    """

    if df.empty:
        return 0

    update_query = """
        UPDATE artist_metadata
        SET
            artist_uri = :artist_uri,
            artist_name = :artist_name,
            popularity = :popularity,
            followers = :followers,
            genres = :genres,
            image_url = :image_url,
            spotify_url = :spotify_url,
            scraped_at = :scraped_at,
            updated_at = CURRENT_TIMESTAMP
        WHERE artist_id = :artist_id;
    """

    rows_updated = 0

    for record in df.to_dict("records"):

        for key, value in record.items():
            if pd.isna(value):
                record[key] = None

        if isinstance(record["genres"], list):
            import json
            record["genres"] = json.dumps(record["genres"])

        execute_sql(
            update_query,
            record,
        )

        rows_updated += 1

    print(
        f"\nUpdated {rows_updated:,} artist metadata rows."
    )

    return rows_updated


# ============================================================
# Main Loader
# ============================================================

def load_artist_metadata():
    """
    Download and update metadata for artists that are missing
    complete metadata.
    """

    missing_artist_ids = get_missing_artist_ids()

    if not missing_artist_ids:

        print(
            "\nArtist metadata is already up to date."
        )

        return pd.DataFrame()

    print(
        f"\nFound "
        f"{len(missing_artist_ids):,} "
        f"artists missing metadata."
    )

    metadata = download_artist_metadata(
        missing_artist_ids
    )

    if metadata.empty:

        print(
            "\nNo artist metadata was downloaded."
        )

        return metadata

    update_artist_metadata(metadata)

    return metadata