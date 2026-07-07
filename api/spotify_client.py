"""
spotify_client.py

Purpose:
--------
This file is responsible for creating ONE authenticated Spotify connection.

Instead of rewriting the login code in every script,
all other Python files will simply import the 'sp' object.

This keeps our project clean and follows the
DRY principle (Don't Repeat Yourself).
"""

# ----------------------------
# Import required libraries
# ----------------------------

import os

import spotipy

from dotenv import load_dotenv

from spotipy.oauth2 import SpotifyOAuth


# --------------------------------------------------
# Load variables stored inside the .env file
# --------------------------------------------------
#
# This allows us to safely store secrets outside
# our code.
#
# Example:
#
# SPOTIPY_CLIENT_ID=xxxxxxxx
# SPOTIPY_CLIENT_SECRET=xxxxxxxx
#
# load_dotenv() reads those values into memory.
#
load_dotenv()


# --------------------------------------------------
# Create ONE authenticated Spotify client.
# --------------------------------------------------
#
# Every other script can now simply do:
#
# from spotify_client import sp
#
# and immediately begin making API requests.
#

sp = spotipy.Spotify(

    auth_manager=SpotifyOAuth(

        client_id=os.getenv("SPOTIPY_CLIENT_ID"),

        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),

        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),

        scope=(
            "user-library-read "
            "user-read-recently-played "
            "user-read-currently-playing"
        )
    )
)
user = sp.current_user()
