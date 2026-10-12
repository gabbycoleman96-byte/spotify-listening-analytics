
from api.spotify_client import sp
from spotipy.exceptions import SpotifyException

queries = [
    ('The Road Back Home', 'Tom Ellenhag'),
    ('Celtic Cowboy', 'Charlotte Funke'),
]

try:
    for track_name, artist_name in queries:
        query = f'track:"{track_name}" artist:"{artist_name}"'

        print(f"\nSearching: {query}")
        results = sp.search(q=query, type="track", limit=10)

        for item in results.get("tracks", {}).get("items", []):
            print({
                "id": item.get("id"),
                "name": item.get("name"),
                "artists": [
                    artist.get("name")
                    for artist in item.get("artists", [])
                ],
                "album": item.get("album", {}).get("name"),
                "release_date": item.get("album", {}).get("release_date"),
                "duration_ms": item.get("duration_ms"),
                "is_playable": item.get("is_playable"),
            })

except SpotifyException as e:
    print("Spotify API error:", e.http_status, str(e))
