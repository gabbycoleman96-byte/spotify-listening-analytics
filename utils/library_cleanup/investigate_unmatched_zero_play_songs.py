"""
investigate_unmatched_zero_play_songs.py

python -m utils.library_cleanup.investigate_unmatched_zero_play_songs

"""



import os
import re
import unicodedata
import pandas as pd
from sqlalchemy import text

from load.database import engine


INPUT_FILE = r"C:\Projects\spotify-listening-analytics\data\manual\279_zero_play_warehouse_investigation.csv"

OUTPUT_FILE = (
    r"C:\Projects\spotify-listening-analytics\data\manual"
    r"\39_unmatched_zero_play_investigation.csv"
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_basic(text):
    """Basic normalization for titles and artist names."""
    if pd.isna(text):
        return ""

    text = str(text).lower().strip()

    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    # Normalize ampersands
    text = text.replace("&", " and ")

    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_title(text):
    """
    More aggressive track-title normalization.

    Removes common Spotify release/version decorations
    while preserving meaningful song titles.
    """
    if pd.isna(text):
        return ""

    text = str(text).strip()

    # Remove featured artist information
    text = re.sub(
        r"\s*[\(\[]?\s*(feat\.?|featuring)\s+.*?[\)\]]?\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove common version/remaster/edit suffixes
    patterns = [
        r"\s*[-–—]\s*original version\s*$",
        r"\s*[-–—]\s*album version\s*$",
        r"\s*[-–—]\s*single version\s*$",
        r"\s*[-–—]\s*radio edit\s*$",
        r"\s*[-–—]\s*album edit\s*$",
        r"\s*[-–—]\s*remastered\s*$",
        r"\s*[-–—]\s*remaster\s*$",
        r"\s*\(\s*original version\s*\)\s*$",
        r"\s*\(\s*album version\s*\)\s*$",
        r"\s*\(\s*single version\s*\)\s*$",
        r"\s*\(\s*radio edit\s*\)\s*$",
        r"\s*\(\s*remastered.*?\)\s*$",
        r"\s*\[\s*remastered.*?\]\s*$",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Normalize "Pt. 2" / "Part II" only when it appears
    # as a trailing formatting decoration.
    text = re.sub(
        r"\s*[-–—]\s*(pt\.?|part)\s*\d+\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return normalize_basic(text)


def artist_tokens(text):
    """Return meaningful artist-name tokens."""
    normalized = normalize_basic(text)

    if not normalized:
        return set()

    # Individual words
    return {
        token
        for token in normalized.split()
        if len(token) >= 3
    }


def artist_overlap(liked_artist, warehouse_artist):
    """
    Calculate overlap between artist names.

    This is intentionally permissive because Spotify can represent
    featured/collaborating artists differently between releases.
    """
    liked_tokens = artist_tokens(liked_artist)
    warehouse_tokens = artist_tokens(warehouse_artist)

    if not liked_tokens or not warehouse_tokens:
        return 0.0

    overlap = liked_tokens & warehouse_tokens

    return len(overlap) / min(
        len(liked_tokens),
        len(warehouse_tokens)
    )


def duration_difference(liked_ms, warehouse_ms):
    """Absolute duration difference in milliseconds."""
    if pd.isna(liked_ms) or pd.isna(warehouse_ms):
        return None

    return abs(float(liked_ms) - float(warehouse_ms))


# ============================================================
# LOAD INPUT
# ============================================================

print()
print("=" * 70)
print("INVESTIGATING 39 UNMATCHED ZERO-PLAY SONGS")
print("=" * 70)
print()

liked_df = pd.read_csv(INPUT_FILE)

# We only want the 39 that currently have no warehouse history.
liked_df = liked_df[
    liked_df["warehouse_status"].eq("NO WAREHOUSE HISTORY")
].copy()

print(f"Unmatched songs loaded: {len(liked_df)}")
print()


# ============================================================
# LOAD WAREHOUSE
# ============================================================

print("Loading warehouse records...")

query = """
    SELECT
        spotify_id,
        track_name,
        artist_name,
        album_name,
        duration_ms,
        played_at
    FROM listening_history_warehouse
    WHERE track_name IS NOT NULL
      AND artist_name IS NOT NULL
"""

with engine.connect() as connection:
    warehouse_df = pd.read_sql(text(query), connection)

print(f"Warehouse records loaded: {len(warehouse_df):,}")
print()


# ============================================================
# BUILD VERSION-LEVEL WAREHOUSE TABLE
# ============================================================

print("Aggregating warehouse listening history by Spotify version...")

warehouse_versions = (
    warehouse_df
    .groupby(
        [
            "spotify_id",
            "track_name",
            "artist_name",
            "album_name",
            "duration_ms",
        ],
        dropna=False
    )
    .agg(
        warehouse_play_count=("played_at", "count"),
        first_played=("played_at", "min"),
        last_played=("played_at", "max"),
    )
    .reset_index()
)

print(
    f"Unique warehouse Spotify versions: "
    f"{len(warehouse_versions):,}"
)
print()


# ============================================================
# ADD NORMALIZED FIELDS
# ============================================================

liked_df["clean_title"] = liked_df["track_name"].apply(normalize_title)
liked_df["clean_artist"] = liked_df["artist_name"].apply(normalize_basic)

warehouse_versions["clean_title"] = (
    warehouse_versions["track_name"].apply(normalize_title)
)

warehouse_versions["clean_artist"] = (
    warehouse_versions["artist_name"].apply(normalize_basic)
)


# ============================================================
# FIND CANDIDATES
# ============================================================

results = []

for _, liked in liked_df.iterrows():

    candidates = []

    liked_title = liked["clean_title"]
    liked_artist = liked["clean_artist"]

    liked_duration = liked["liked_duration_ms"]

    # --------------------------------------------------------
    # LEVEL 1: CLEAN TITLE + EXACT NORMALIZED ARTIST
    # --------------------------------------------------------

    exact_artist = warehouse_versions[
        (warehouse_versions["clean_title"] == liked_title)
        & (warehouse_versions["clean_artist"] == liked_artist)
    ].copy()

    for _, candidate in exact_artist.iterrows():

        diff = duration_difference(
            liked_duration,
            candidate["duration_ms"]
        )

        candidates.append(
            (
                candidate,
                "CLEAN TITLE + ARTIST",
                100,
                diff,
            )
        )

    # --------------------------------------------------------
    # LEVEL 2: CLEAN TITLE + ARTIST OVERLAP
    # --------------------------------------------------------

    if not candidates:

        title_matches = warehouse_versions[
            warehouse_versions["clean_title"] == liked_title
        ].copy()

        for _, candidate in title_matches.iterrows():

            overlap = artist_overlap(
                liked["artist_name"],
                candidate["artist_name"]
            )

            if overlap > 0:

                diff = duration_difference(
                    liked_duration,
                    candidate["duration_ms"]
                )

                # Duration strongly increases confidence.
                if diff is not None and diff <= 2000:
                    score = 90
                    reason = "CLEAN TITLE + ARTIST OVERLAP + DURATION"
                elif diff is not None and diff <= 5000:
                    score = 75
                    reason = "CLEAN TITLE + ARTIST OVERLAP"
                else:
                    score = 60
                    reason = "CLEAN TITLE + ARTIST OVERLAP"

                candidates.append(
                    (
                        candidate,
                        reason,
                        score,
                        diff,
                    )
                )

    # --------------------------------------------------------
    # LEVEL 3: TITLE SIMILARITY
    # --------------------------------------------------------

    if not candidates:

        # Look for warehouse titles containing the liked title
        # or the liked title containing the warehouse title.
        title_matches = warehouse_versions[
            warehouse_versions["clean_title"].apply(
                lambda x:
                    (
                        liked_title in x
                        or x in liked_title
                    )
                    and len(liked_title) >= 5
            )
        ].copy()

        for _, candidate in title_matches.iterrows():

            overlap = artist_overlap(
                liked["artist_name"],
                candidate["artist_name"]
            )

            diff = duration_difference(
                liked_duration,
                candidate["duration_ms"]
            )

            if overlap > 0.0:

                if diff is not None and diff <= 2000:
                    score = 70
                    reason = "SIMILAR TITLE + ARTIST OVERLAP + DURATION"
                else:
                    score = 50
                    reason = "SIMILAR TITLE + ARTIST OVERLAP"

                candidates.append(
                    (
                        candidate,
                        reason,
                        score,
                        diff,
                    )
                )

    # --------------------------------------------------------
    # NO MATCH
    # --------------------------------------------------------

    if not candidates:

        results.append(
            {
                "liked_spotify_id": liked["liked_spotify_id"],
                "liked_track_name": liked["track_name"],
                "liked_artist_name": liked["artist_name"],
                "liked_album_name": liked["liked_album_name"],
                "liked_duration_ms": liked_duration,
                "match_status": "NO MATCH",
                "match_reason": "NO CANDIDATE FOUND",
                "confidence_score": 0,
                "warehouse_spotify_id": None,
                "warehouse_track_name": None,
                "warehouse_artist_name": None,
                "warehouse_album_name": None,
                "warehouse_duration_ms": None,
                "duration_difference_ms": None,
                "warehouse_play_count": 0,
                "first_played": None,
                "last_played": None,
            }
        )

        continue

    # --------------------------------------------------------
    # KEEP TOP 5 CANDIDATES
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: (
            x[2],
            -(x[3] if x[3] is not None else 999999999),
            x[0]["warehouse_play_count"],
        ),
        reverse=True,
    )

    for candidate, reason, score, diff in candidates[:5]:

        results.append(
            {
                "liked_spotify_id": liked["liked_spotify_id"],
                "liked_track_name": liked["track_name"],
                "liked_artist_name": liked["artist_name"],
                "liked_album_name": liked["liked_album_name"],
                "liked_duration_ms": liked_duration,
                "match_status": "CANDIDATE FOUND",
                "match_reason": reason,
                "confidence_score": score,
                "warehouse_spotify_id": candidate["spotify_id"],
                "warehouse_track_name": candidate["track_name"],
                "warehouse_artist_name": candidate["artist_name"],
                "warehouse_album_name": candidate["album_name"],
                "warehouse_duration_ms": candidate["duration_ms"],
                "duration_difference_ms": diff,
                "warehouse_play_count": candidate["warehouse_play_count"],
                "first_played": candidate["first_played"],
                "last_played": candidate["last_played"],
            }
        )


# ============================================================
# SAVE
# ============================================================

result_df = pd.DataFrame(results)

result_df = result_df.sort_values(
    [
        "liked_track_name",
        "confidence_score",
        "warehouse_play_count",
    ],
    ascending=[True, False, False],
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False,
)

print()
print("=" * 70)
print("INVESTIGATION COMPLETE")
print("=" * 70)
print()

print(f"Songs investigated:       {len(liked_df)}")
print(
    "Songs with candidates:   ",
    result_df["liked_spotify_id"].nunique()
)
print(
    "Songs with no candidates:",
    (
        result_df["match_status"]
        .eq("NO MATCH")
        .sum()
    )
)

print()
print("Output saved to:")
print(OUTPUT_FILE)
print()

print("Confidence summary:")
print(
    result_df[
        result_df["match_status"].eq("CANDIDATE FOUND")
    ]["confidence_score"].value_counts().sort_index(
        ascending=False
    )
)

print()
print("=" * 70)