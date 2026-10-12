
from api.spotify_client import sp
from spotipy.exceptions import SpotifyException

album_id = "2wbmxqyZoUpc1FfR15xof8"

try:
    album = sp.album(album_id)

    print("Album ID:", repr(album.get("id")))
    print("Album name:", repr(album.get("name")))
    print("Release date:", repr(album.get("release_date")))
    print("Total tracks:", repr(album.get("total_tracks")))

    print("\nTracks returned by Spotify:")
    for track in album.get("tracks", {}).get("items", []):
        print({
            "id": track.get("id"),
            "name": track.get("name"),
            "duration_ms": track.get("duration_ms"),
            "is_playable": track.get("is_playable"),
            "artists": [
                artist.get("name")
                for artist in track.get("artists", [])
            ],
        })

except SpotifyException as e:
    print("Spotify API error:", e.http_status, str(e))
