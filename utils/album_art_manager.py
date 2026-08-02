"""
album_art_manager.py

Downloads album artwork from Spotify, stores it locally,
and updates album_metadata with the GitHub raw URL.
"""

from pathlib import Path
import requests

from tqdm import tqdm
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

from load.reader import read_query
from load.loader import execute_sql


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

IMAGE_DIR = Path("assets/album_art")

RAW_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "gabbycoleman96-byte/"
    "spotify-listening-analytics/"
    "main/"
    "assets/album_art"
)

session = requests.Session()

retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry)

session.mount("https://", adapter)
session.mount("http://", adapter)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def ensure_directory():
    """Create the album art directory if it doesn't exist."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def github_url(album_id):
    """Return the GitHub raw URL for an album image."""
    return f"{RAW_BASE_URL}/{album_id}.jpg"


# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------

def get_missing_album_art():
    """
    Albums that still need hosted artwork.
    """

    query = """
        SELECT
            album_id,
            spotify_album_art_url
        FROM album_metadata
        WHERE spotify_album_art_url IS NOT NULL
        AND album_art_url IS NULL
    """

    return read_query(query)


# -------------------------------------------------------------------
# Download
# -------------------------------------------------------------------

def download_image(url, destination):
    """
    Download a single image.
    """

    response = session.get(url, timeout=30)
    response.raise_for_status()

    with open(destination, "wb") as f:
        f.write(response.content)


def download_missing_album_art():

    ensure_directory()

    albums = get_missing_album_art()

    if albums.empty:
        print("✓ No missing album art.")
        return 0
    
    downloaded = 0

    for _, album in tqdm(
        albums.iterrows(),
        total=len(albums),
        desc="Downloading album art"
    ):

        album_id = album["album_id"]
        spotify_url = album["spotify_album_art_url"]

        filename = IMAGE_DIR / f"{album_id}.jpg"

        if filename.exists():
            continue

        try:
            download_image(spotify_url, filename)
            downloaded += 1
            
            time.sleep(0.1)

        except Exception as e:
            print(f"Failed: {album_id} ({e})")

    return downloaded

# -------------------------------------------------------------------
# Update URLs
# -------------------------------------------------------------------

def update_album_art_urls():
    
    updated = 0
    
    albums = get_missing_album_art()
    

    for _, album in albums.iterrows():

        album_id = album["album_id"]

        local_file = IMAGE_DIR / f"{album_id}.jpg"

        if not local_file.exists():
            continue

        execute_sql(
            """
            UPDATE album_metadata
            SET album_art_url = :album_art_url
            WHERE album_id = :album_id
            """,
            {
                "album_art_url": github_url(album_id),
                "album_id": album_id,
            }
        )
        
        updated += 1

    return updated


# -------------------------------------------------------------------
# Run
# -------------------------------------------------------------------

def process_album_art():

    downloaded = download_missing_album_art()
    updated = update_album_art_urls()

    if downloaded > 0:
        print()
        print(f"Downloaded {downloaded} new album covers.")
        print("Commit and push the new images to GitHub.")
        print("The next ETL run will automatically update their URLs.")

    return updated