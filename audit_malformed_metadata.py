
import time
import re
import unicodedata

import pandas as pd

from api.spotify_client import sp
from load.loader import fetch_dataframe
from spotipy.exceptions import SpotifyException


OUTPUT_FILE = "malformed_metadata_audit.csv"


def normalize(value):
    """Normalize text for comparison without removing meaningful words."""
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


query = """
    SELECT
        tm.spotify_id AS original_id,
        MAX(w.track_name) AS track_name,
        MAX(w.artist_name) AS artist_name,
        COUNT(*) AS play_count,
        MIN(w.ms_played) AS min_ms_played,
        MAX(w.ms_played) AS max_ms_played,
        COUNT(DISTINCT w.ms_played) AS distinct_play_durations
    FROM track_metadata tm
    JOIN listening_history_warehouse w
        ON w.spotify_id = tm.spotify_id
    WHERE
        (tm.track_name IS NULL OR TRIM(tm.track_name) = '')
        AND (tm.duration_ms IS NULL OR tm.duration_ms = 0)
    GROUP BY tm.spotify_id
    ORDER BY play_count DESC, tm.spotify_id
"""

tracks = fetch_dataframe(query)
print(f"Found {len(tracks)} malformed metadata records.")

results = []
request_count = 0
stop_audit = False

for index, row in tracks.iterrows():
    original_id = row["original_id"]
    track_name = str(row["track_name"] or "").strip()
    artist_name = str(row["artist_name"] or "").strip()

    print(
        f"\n[{index + 1}/{len(tracks)}] "
        f"{track_name} | {artist_name}"
    )

    queries = [
        ("title_artist", f'track:"{track_name}" artist:"{artist_name}"'),
        ("title_only", f'track:"{track_name}"'),
    ]

    seen_candidate_ids = set()

    for search_type, search_query in queries:
        try:
            response = sp.search(
                q=search_query,
                type="track",
                limit=10,
            )
            request_count += 1

        except SpotifyException as exc:
            print(
                f"Spotify API error: {exc.http_status} {exc}"
            )

            if exc.http_status == 429:
                print("Rate limit reached. Stopping audit.")
                stop_audit = True
                break

            continue

        candidates = response.get("tracks", {}).get("items", [])

        print(f"  {search_type}: {len(candidates)} results")

        for candidate in candidates:
            candidate_id = candidate.get("id")

            if not candidate_id or candidate_id in seen_candidate_ids:
                continue

            seen_candidate_ids.add(candidate_id)

            candidate_name = candidate.get("name") or ""
            candidate_artists = [
                artist.get("name", "")
                for artist in candidate.get("artists", [])
            ]
            candidate_artist_text = ", ".join(candidate_artists)
            album = candidate.get("album") or {}
            duration_ms = candidate.get("duration_ms")

            title_match = (
                normalize(candidate_name) == normalize(track_name)
            )
            artist_match = (
                normalize(artist_name) in {
                    normalize(artist)
                    for artist in candidate_artists
                }
            )

            duration_difference = None
            if duration_ms is not None:
                duration_difference = int(duration_ms) - int(
                    row["max_ms_played"]
                )

            result = {
                "original_id": original_id,
                "original_track_name": track_name,
                "original_artist_name": artist_name,
                "play_count": int(row["play_count"]),
                "min_ms_played": int(row["min_ms_played"]),
                "max_ms_played": int(row["max_ms_played"]),
                "distinct_play_durations": int(
                    row["distinct_play_durations"]
                ),
                "search_type": search_type,
                "candidate_id": candidate_id,
                "candidate_name": candidate_name,
                "candidate_artists": candidate_artist_text,
                "title_match": title_match,
                "artist_match": artist_match,
                "album": album.get("name"),
                "release_date": album.get("release_date"),
                "duration_ms": duration_ms,
                "duration_minus_longest_play_ms": duration_difference,
                "is_playable": candidate.get("is_playable"),
                "candidate_uri": candidate.get("uri"),
                "candidate_url": (
                    candidate.get("external_urls", {}).get("spotify")
                ),
            }

            results.append(result)

            print(
                f"    {candidate_name} | {candidate_artist_text} | "
                f"{duration_ms} ms | "
                f"title_match={title_match} | "
                f"artist_match={artist_match}"
            )

        time.sleep(0.2)

    if stop_audit:
        break

    time.sleep(0.2)

if results:
    output = pd.DataFrame(results)
    output.to_csv(OUTPUT_FILE, index=False)

    print(f"\nSearch requests made: {request_count}")
    print(f"Candidate records saved: {len(output)}")
    print(f"Output: {OUTPUT_FILE}")
else:
    print("\nNo candidate records were collected.")
