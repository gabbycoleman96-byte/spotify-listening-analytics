"""
Spotify Song Identity Resolution
================================

Read-only investigation tool for connecting Spotify IDs that represent
the same underlying song across liked_songs and listening_history_warehouse.

This script does NOT modify MySQL or Spotify.

Run from the project root:

    python -m transform.song_identity

Output:

    C:/Projects/spotify-listening-analytics/data/investigative/song_identity_review.csv
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load.database import engine


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "data" / "investigative"
OUTPUT_FILE = OUTPUT_DIR / "song_identity_review.csv"

OVERRIDE_FILE = (
    PROJECT_ROOT
    / "data"
    / "manual"
    / "song_identity_overrides.csv"
)

STRONG_DURATION_TOLERANCE_MS = 1500
REVIEW_DURATION_TOLERANCE_MS = 3000

FUZZY_TITLE_THRESHOLD = 0.90

# These indicate that two Spotify records may actually be different
# recordings. They can still produce a candidate, but the match should
# normally require human review.
RISKY_VERSION_PATTERNS = [
    r"\blive\b",
    r"\bacoustic\b",
    r"\bremix\b",
    r"\bradio edit\b",
    r"\bextended\b",
    r"\bedit\b",
    r"\balternate\b",
    r"\bversion\b",
    r"\bcover\b",
    r"\bdemo\b",
    r"\binstrumental\b",
]


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_unicode(value) -> str:
    """Normalize Unicode punctuation and compatibility characters."""

    if pd.isna(value):
        return ""

    value = str(value)

    value = unicodedata.normalize("NFKC", value)

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def normalize_text(value) -> str:
    """Basic comparison normalization."""

    value = normalize_unicode(value)

    value = value.lower().strip()

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_compact_title(value) -> str:
    """
    Create a compact comparison key for titles where punctuation or
    spaces separate individual letters.

    Examples:
        A-O-K   -> aok
        A O K   -> aok
        A.O.K.  -> aok
        aok     -> aok
    """

    value = normalize_text(value)

    # Remove non-alphanumeric characters.
    value = re.sub(r"[^a-z0-9]+", "", value)

    return value


def normalize_artist_set(value) -> set[str]:
    """
    Convert an artist field into a set of normalized artist names.

    Spotify metadata commonly stores collaborations as:

        Artist A, Artist B

    We intentionally keep this conservative. We do not attempt to split
    arbitrary artist names containing punctuation.
    """

    value = normalize_unicode(value)

    if not value:
        return set()

    # Normalize common collaboration separators.
    value = re.sub(
        r"\s+(?:feat\.?|featuring|with)\s+",
        ",",
        value,
        flags=re.IGNORECASE,
    )

    parts = re.split(r",|&", value)

    artists = set()

    for part in parts:
        part = normalize_text(part)

        if part:
            artists.add(part)

    return artists


def artist_overlap(liked_artists: set[str], warehouse_artists: set[str]) -> set[str]:
    """Return artists appearing in both metadata records."""

    return liked_artists.intersection(warehouse_artists)


# ---------------------------------------------------------------------------
# Title normalization
# ---------------------------------------------------------------------------

def remove_feature_metadata(title: str) -> str:
    """
    Remove title-side feature notation.

    Example:

        Bad Habits (feat. Bring Me The Horizon)

    becomes:

        Bad Habits
    """

    title = normalize_unicode(title)

    title = re.sub(
        r"\s*[\(\[]\s*(?:feat\.?|featuring|with)\b.*?[\)\]]",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s*[-,]\s*(?:feat\.?|featuring|with)\b.*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    return title.strip()


def remove_benign_version_metadata(title: str) -> str:
    """
    Remove version descriptors that generally describe the Spotify
    representation rather than a fundamentally different song.
    """

    title = normalize_unicode(title)

    # Motion-picture metadata
    title = re.sub(
        r"\s*[\(\[]\s*from the motion picture\b.*?[\)\]]",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # Recorded-at metadata
    title = re.sub(
        r"\s*-\s*recorded at\b.*$",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # Common remaster/version suffixes
    patterns = [
        r"\s*-\s*album version\s*$",
        r"\s*-\s*remastered(?:\s+\d{4})?\s*$",
        r"\s*-\s*original version\s*$",
        r"\s*-\s*original 7[\"']?\s*version\s*$",
        r"\s*\(\s*remastered(?:\s+\d{4})?\s*\)\s*$",
        r"\s*\(\s*original version\s*\)\s*$",
    ]

    changed = True

    while changed:
        changed = False

        for pattern in patterns:
            new_title = re.sub(
                pattern,
                "",
                title,
                flags=re.IGNORECASE,
            )

            if new_title != title:
                changed = True
                title = new_title

    return title.strip()


def remove_risky_version_metadata(title: str) -> str:
    """
    Remove version descriptors only for candidate generation.

    These are NOT considered safe enough for automatic identity matching.
    """

    title = normalize_unicode(title)

    patterns = [
        r"\s*-\s*live\b.*$",
        r"\s*\(\s*live\b.*?[\)\]]",
        r"\s*-\s*acoustic\b.*$",
        r"\s*\(\s*acoustic\b.*?[\)\]]",
        r"\s*-\s*radio edit\b.*$",
        r"\s*-\s*extended\b.*$",
        r"\s*-\s*remix\b.*$",
        r"\s*\(\s*remix\b.*?[\)\]]",
    ]

    for pattern in patterns:
        title = re.sub(
            pattern,
            "",
            title,
            flags=re.IGNORECASE,
        )

    return title.strip()


def normalize_title(value) -> str:
    """Normalize a title without removing version information."""

    value = normalize_text(value)

    value = remove_feature_metadata(value)

    value = re.sub(r"[^\w\s']+", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_base_title(value) -> str:
    """
    Create a broader title key for candidate generation.

    This removes metadata such as remaster/original/movie/recorded-at
    descriptors, while preserving meaningful song distinctions whenever
    possible.
    """

    value = normalize_unicode(value)

    value = remove_feature_metadata(value)

    value = remove_benign_version_metadata(value)

    value = remove_risky_version_metadata(value)

    value = normalize_text(value)

    # Spotify occasionally has "Intro/Prelude 12/21" versus
    # "Prelude 12/21".
    value = re.sub(
        r"^intro\s*/\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Clean punctuation after metadata removal.
    value = re.sub(r"[^\w\s']+", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def title_has_risky_version(value) -> bool:
    """Return True when a title contains a potentially different recording."""

    title = normalize_unicode(value)

    for pattern in RISKY_VERSION_PATTERNS:
        if re.search(pattern, title, flags=re.IGNORECASE):
            return True

    return False


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------

def duration_difference(liked_duration, warehouse_duration):
    """Return absolute duration difference in milliseconds."""

    if pd.isna(liked_duration) or pd.isna(warehouse_duration):
        return None

    try:
        return abs(float(liked_duration) - float(warehouse_duration))
    except (TypeError, ValueError):
        return None


def duration_is_close(
    difference,
    tolerance: int,
) -> bool:
    """Check duration tolerance."""

    if difference is None:
        return False

    return difference <= tolerance


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def title_similarity(title_a: str, title_b: str) -> float:
    """Return SequenceMatcher similarity between normalized titles."""

    if not title_a or not title_b:
        return 0.0

    return SequenceMatcher(
        None,
        title_a,
        title_b,
    ).ratio()


# ---------------------------------------------------------------------------
# Candidate evaluation
# ---------------------------------------------------------------------------

def evaluate_candidate(
    liked_row,
    warehouse_row,
):
    """
    Evaluate one liked-song / warehouse-song pairing.

    Returns a dictionary describing the relationship.
    """

    liked_title = liked_row["normalized_title"]
    warehouse_title = warehouse_row["normalized_title"]

    liked_base_title = liked_row["base_title"]
    warehouse_base_title = warehouse_row["base_title"]

    liked_artists = liked_row["artist_set"]
    warehouse_artists = warehouse_row["artist_set"]

    shared_artists = artist_overlap(
        liked_artists,
        warehouse_artists,
    )

    if not shared_artists:
        return None

    exact_title = (
        liked_title == warehouse_title
        and bool(liked_title)
    )

    exact_base_title = (
        liked_base_title == warehouse_base_title
        and bool(liked_base_title)
    )
    
    compact_liked_title = normalize_compact_title(liked_row["track_name"])
    compact_warehouse_title = normalize_compact_title(
        warehouse_row["track_name"]
    )

    compact_title_match = (
        compact_liked_title == compact_warehouse_title
        and bool(compact_liked_title)
    )

    similarity = title_similarity(
        liked_base_title,
        warehouse_base_title,
    )

    difference = duration_difference(
        liked_row["duration_ms"],
        warehouse_row["duration_ms"],
    )

    liked_risky = title_has_risky_version(
        liked_row["track_name"]
    )

    warehouse_risky = title_has_risky_version(
        warehouse_row["track_name"]
    )

    risky_version_difference = (
        liked_risky != warehouse_risky
    )

    # ---------------------------------------------------------------
    # Tier 1: exact normalized title + artist overlap
    # ---------------------------------------------------------------

    if exact_title:

        if difference is None:
            return {
                "tier": 2,
                "status": "STRONG MATCH",
                "method": "EXACT TITLE + ARTIST OVERLAP",
                "reason": (
                    "Exact normalized title and artist identity agree. "
                    "Duration was unavailable."
                ),
                "title_similarity": 1.0,
                "duration_difference_ms": None,
                "shared_artists": shared_artists,
                "risky_version_difference": risky_version_difference,
            }

        if duration_is_close(
            difference,
            STRONG_DURATION_TOLERANCE_MS,
        ):

            if risky_version_difference:
                return {
                    "tier": 4,
                    "status": "REVIEW",
                    "method": (
                        "EXACT TITLE + ARTIST OVERLAP + "
                        "CLOSE DURATION"
                    ),
                    "reason": (
                        "Title, artist, and duration agree, but one "
                        "Spotify title contains version metadata that "
                        "could represent a different recording."
                    ),
                    "title_similarity": 1.0,
                    "duration_difference_ms": difference,
                    "shared_artists": shared_artists,
                    "risky_version_difference": True,
                }

            return {
                "tier": 2,
                "status": "STRONG MATCH",
                "method": (
                    "EXACT TITLE + ARTIST OVERLAP + DURATION"
                ),
                "reason": (
                    "Exact normalized title and artist identity agree "
                    "and duration is within the strong tolerance."
                ),
                "title_similarity": 1.0,
                "duration_difference_ms": difference,
                "shared_artists": shared_artists,
                "risky_version_difference": False,
            }

        if duration_is_close(
            difference,
            REVIEW_DURATION_TOLERANCE_MS,
        ):
            return {
                "tier": 3,
                "status": "REVIEW",
                "method": (
                    "EXACT TITLE + ARTIST OVERLAP + "
                    "MODERATE DURATION DIFFERENCE"
                ),
                "reason": (
                    "Title and artist identity agree, but duration "
                    "difference is too large for automatic matching."
                ),
                "title_similarity": 1.0,
                "duration_difference_ms": difference,
                "shared_artists": shared_artists,
                "risky_version_difference": risky_version_difference,
            }

        return {
            "tier": 4,
            "status": "REVIEW",
            "method": "EXACT TITLE + ARTIST OVERLAP",
            "reason": (
                "Title and artist identity agree, but duration differs "
                "too much for automatic matching."
            ),
            "title_similarity": 1.0,
            "duration_difference_ms": difference,
            "shared_artists": shared_artists,
            "risky_version_difference": risky_version_difference,
        }
    
    # ---------------------------------------------------------------
    # Compact title + artist overlap
    # ---------------------------------------------------------------

    if compact_title_match:

        if difference is not None and duration_is_close(
            difference,
            STRONG_DURATION_TOLERANCE_MS,
        ):

            if risky_version_difference:
                return {
                    "tier": 4,
                    "status": "REVIEW",
                    "method": (
                        "COMPACT TITLE + ARTIST OVERLAP + DURATION"
                    ),
                    "reason": (
                        "Titles match after compact punctuation normalization, "
                        "artist identity agrees, and duration is within the "
                        "strong tolerance."
                    ),
                    "title_similarity": similarity,
                    "duration_difference_ms": difference,
                    "shared_artists": shared_artists,
                    "risky_version_difference": True,
                }

            return {
                "tier": 2,
                "status": "STRONG MATCH",
                "method": (
                    "COMPACT TITLE + ARTIST OVERLAP + DURATION"
                ),
                "reason": (
                    "Titles match after compact punctuation normalization, "
                    "artist identity agrees, and duration is within the "
                    "strong tolerance."
                ),
                "title_similarity": similarity,
                "duration_difference_ms": difference,
                "shared_artists": shared_artists,
                "risky_version_difference": False,
            }

    # ---------------------------------------------------------------
    # Tier 2: base title + artist overlap
    # ---------------------------------------------------------------

    if exact_base_title:

        if difference is not None and duration_is_close(
            difference,
            STRONG_DURATION_TOLERANCE_MS,
        ):

            if risky_version_difference:
                return {
                    "tier": 4,
                    "status": "REVIEW",
                    "method": (
                        "BASE TITLE + ARTIST OVERLAP + "
                        "DURATION"
                    ),
                    "reason": (
                        "Version metadata was removed to connect the "
                        "titles, but the version difference may represent "
                        "a different recording."
                    ),
                    "title_similarity": similarity,
                    "duration_difference_ms": difference,
                    "shared_artists": shared_artists,
                    "risky_version_difference": True,
                }

            return {
                "tier": 2,
                "status": "STRONG MATCH",
                "method": (
                    "BASE TITLE + ARTIST OVERLAP + DURATION"
                ),
                "reason": (
                    "Titles differ only by normalized version metadata; "
                    "artist identity and duration agree."
                ),
                "title_similarity": similarity,
                "duration_difference_ms": difference,
                "shared_artists": shared_artists,
                "risky_version_difference": False,
            }

        if difference is not None and duration_is_close(
            difference,
            REVIEW_DURATION_TOLERANCE_MS,
        ):
            return {
                "tier": 3,
                "status": "REVIEW",
                "method": (
                    "BASE TITLE + ARTIST OVERLAP + "
                    "MODERATE DURATION DIFFERENCE"
                ),
                "reason": (
                    "Base titles and artists agree, but duration "
                    "requires human review."
                ),
                "title_similarity": similarity,
                "duration_difference_ms": difference,
                "shared_artists": shared_artists,
                "risky_version_difference": risky_version_difference,
            }

        return {
            "tier": 4,
            "status": "REVIEW",
            "method": "BASE TITLE + ARTIST OVERLAP",
            "reason": (
                "Base titles and artists agree, but duration does not "
                "provide enough support for automatic matching."
            ),
            "title_similarity": similarity,
            "duration_difference_ms": difference,
            "shared_artists": shared_artists,
            "risky_version_difference": risky_version_difference,
        }

    # ---------------------------------------------------------------
    # Tier 3: fuzzy title + artist overlap
    # ---------------------------------------------------------------

    if similarity >= FUZZY_TITLE_THRESHOLD:

        if difference is not None and duration_is_close(
            difference,
            REVIEW_DURATION_TOLERANCE_MS,
        ):
            return {
                "tier": 4,
                "status": "REVIEW",
                "method": (
                    "FUZZY TITLE + ARTIST OVERLAP + DURATION"
                ),
                "reason": (
                    "Titles are highly similar and artist identity "
                    "overlaps, but the match requires review."
                ),
                "title_similarity": similarity,
                "duration_difference_ms": difference,
                "shared_artists": shared_artists,
                "risky_version_difference": risky_version_difference,
            }

    return None


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized comparison fields."""

    df = df.copy()

    df["track_name"] = df["track_name"].fillna("").astype(str)
    df["artist_name"] = df["artist_name"].fillna("").astype(str)

    df["normalized_title"] = df["track_name"].apply(
        normalize_title
    )

    df["base_title"] = df["track_name"].apply(
        normalize_base_title
    )

    df["artist_set"] = df["artist_name"].apply(
        normalize_artist_set
    )

    return df


def build_candidate_indexes(warehouse_df):
    """Build title indexes for efficient candidate lookup."""

    exact_index = defaultdict(list)
    base_index = defaultdict(list)
    compact_index = defaultdict(list)

    for index, row in warehouse_df.iterrows():

        if row["normalized_title"]:
            exact_index[row["normalized_title"]].append(index)

        if row["base_title"]:
            base_index[row["base_title"]].append(index)

        compact_title = normalize_compact_title(
            row["track_name"]
        )

        if compact_title:
            compact_index[compact_title].append(index)

    return exact_index, base_index, compact_index


def find_candidates(
    liked_row,
    warehouse_df,
    exact_index,
    base_index,
    compact_index,
):
    """
    Generate candidate warehouse records.

    Candidate generation is intentionally broader than automatic matching.
    The evaluator decides whether each candidate is safe.
    """

    candidate_indexes = set()

    exact_title = liked_row["normalized_title"]
    base_title = liked_row["base_title"]
    compact_title = normalize_compact_title(
        liked_row["track_name"]
    )

    # Exact title candidates
    for index in exact_index.get(exact_title, []):
        candidate_indexes.add(index)

    # Base title candidates
    for index in base_index.get(base_title, []):
        candidate_indexes.add(index)

    # Compact title candidates
    for index in compact_index.get(compact_title, []):
        candidate_indexes.add(index)

    # If no deterministic candidates exist, use fuzzy comparison.
    if not candidate_indexes and base_title:

        for index, warehouse_row in warehouse_df.iterrows():

            similarity = title_similarity(
                base_title,
                warehouse_row["base_title"],
            )

            if similarity >= FUZZY_TITLE_THRESHOLD:
                candidate_indexes.add(index)

    return candidate_indexes


# ---------------------------------------------------------------------------
# Canonical version selection
# ---------------------------------------------------------------------------

def choose_canonical_candidate(candidates):
    """
    Choose a canonical Spotify ID from a resolved identity group.

    Priority:

        1. Highest warehouse play count
        2. Most recently played
        3. Deterministic Spotify ID

    This is deliberately separate from identity matching.
    """

    if not candidates:
        return None

    candidate_df = pd.DataFrame(candidates).copy()

    candidate_df["play_count"] = pd.to_numeric(
        candidate_df["play_count"],
        errors="coerce",
    ).fillna(0)

    candidate_df["last_played"] = pd.to_datetime(
        candidate_df["last_played"],
        errors="coerce",
    )

    candidate_df = candidate_df.sort_values(
        by=[
            "play_count",
            "last_played",
            "spotify_id",
        ],
        ascending=[
            False,
            False,
            True,
        ],
        kind="stable",
    )

    return candidate_df.iloc[0]["spotify_id"]


def load_identity_overrides():
    """
    Load manually approved song identity relationships.

    Overrides are keyed by liked Spotify ID and contain the warehouse
    Spotify IDs that have been manually approved as the same song identity.
    """

    if not OVERRIDE_FILE.exists():
        return {}

    overrides = {}

    with OVERRIDE_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            liked_id = row["liked_spotify_id"].strip()

            if not liked_id:
                continue

            approved_ids = [
                spotify_id.strip()
                for spotify_id in row["approved_spotify_ids"].split("|")
                if spotify_id.strip()
            ]

            overrides[liked_id] = {
                "decision": row["decision"].strip(),
                "approved_spotify_ids": approved_ids,
                "canonical_spotify_id": (
                    row["canonical_spotify_id"].strip()
                    if row["canonical_spotify_id"]
                    else None
                ),
                "reason": row["reason"].strip(),
            }

    return overrides


# ---------------------------------------------------------------------------
# Main investigation
# ---------------------------------------------------------------------------

def main():

    print("=" * 60)
    print("SONG IDENTITY INVESTIGATION")
    print("=" * 60)
    print()

    # The project-wide SQLAlchemy engine is imported from load.database.
    # No database configuration is duplicated here.

    # ---------------------------------------------------------------
    # Load liked songs
    # ---------------------------------------------------------------

    print("Loading liked songs...")

    liked_query = text(
        """
        SELECT
            spotify_id,
            track_name,
            artist_name,
            album_name,
            release_date,
            added_to_library,
            duration_ms
        FROM liked_songs
        WHERE spotify_id IS NOT NULL
        """
    )

    liked_df = pd.read_sql(
        liked_query,
        engine,
    )

    print(f"Liked songs loaded: {len(liked_df):,}")
    print()

    # ---------------------------------------------------------------
    # Load warehouse metadata
    # ---------------------------------------------------------------

    print("Loading listening-history warehouse...")

    warehouse_query = text(
        """
        SELECT
            spotify_id,
            track_name,
            artist_name,
            album_name,
            duration_ms,
            COUNT(*) AS play_count,
            MIN(played_at) AS first_played,
            MAX(played_at) AS last_played
        FROM listening_history_warehouse
        WHERE spotify_id IS NOT NULL
        GROUP BY
            spotify_id,
            track_name,
            artist_name,
            album_name,
            duration_ms
        """
    )

    warehouse_df = pd.read_sql(
        warehouse_query,
        engine,
    )

    print(
        f"Warehouse Spotify IDs loaded: "
        f"{warehouse_df['spotify_id'].nunique():,}"
    )
    print()

    # ---------------------------------------------------------------
    # Prepare metadata
    # ---------------------------------------------------------------

    liked_df = prepare_dataframe(
        liked_df
    )

    warehouse_df = prepare_dataframe(
        warehouse_df
    )

    exact_index, base_index, compact_index = build_candidate_indexes(
        warehouse_df
    )

    # ---------------------------------------------------------------
    # Resolve identities
    # ---------------------------------------------------------------

    print("Resolving song identities...")
    print()

    identity_overrides = load_identity_overrides()

    print(
        f"Identity overrides loaded: "
        f"{len(identity_overrides):,}"
    )
    print()

    results = []

    for _, liked_row in liked_df.iterrows():

        liked_id = liked_row["spotify_id"]

        # -----------------------------------------------------------
        # Exact Spotify ID match
        # -----------------------------------------------------------

        exact_id_matches = warehouse_df[
            warehouse_df["spotify_id"] == liked_id
        ]

        if not exact_id_matches.empty:

            exact_id_play_count = (
                exact_id_matches["play_count"]
                .fillna(0)
                .sum()
            )

            exact_id_first_played = (
                pd.to_datetime(
                    exact_id_matches["first_played"],
                    errors="coerce",
                )
                .min()
            )

            exact_id_last_played = (
                pd.to_datetime(
                    exact_id_matches["last_played"],
                    errors="coerce",
                )
                .max()
            )

            warehouse_row = exact_id_matches.sort_values(
                by=[
                    "play_count",
                    "last_played",
                ],
                ascending=[
                    False,
                    False,
                ],
                kind="stable",
            ).iloc[0]

            results.append({
                "liked_spotify_id": liked_id,
                "liked_track_name": liked_row["track_name"],
                "liked_artist_name": liked_row["artist_name"],
                "liked_album_name": liked_row["album_name"],
                "liked_duration_ms": liked_row["duration_ms"],

                "warehouse_spotify_id": liked_id,
                "warehouse_track_name": warehouse_row["track_name"],
                "warehouse_artist_name": warehouse_row["artist_name"],
                "warehouse_album_name": warehouse_row["album_name"],
                "warehouse_duration_ms": warehouse_row["duration_ms"],

                "warehouse_play_count": exact_id_play_count,
                "first_played": exact_id_first_played,
                "last_played": exact_id_last_played,

                "identity_status": "EXACT MATCH",
                "match_method": "EXACT SPOTIFY ID",
                "match_reason": (
                    "Liked Spotify ID exists directly in the "
                    "listening-history warehouse."
                ),

                "title_similarity": 1.0,
                "duration_difference_ms": 0,
                "shared_artists": liked_row["artist_name"],

                "candidate_count": 1,
                "candidate_spotify_ids": liked_id,

                "canonical_spotify_id": liked_id,
                "canonical_play_count": exact_id_play_count,

                "review_required": False,
            })

            continue
        
        # -----------------------------------------------------------
        # Manual identity override
        # -----------------------------------------------------------

        override = identity_overrides.get(liked_id)

        if (
            override
            and override["decision"].upper() == "APPROVE"
        ):

            approved_ids = set(
                override["approved_spotify_ids"]
            )

            approved_candidates = warehouse_df[
                warehouse_df["spotify_id"].isin(
                    approved_ids
                )
            ].copy()

            if not approved_candidates.empty:

                canonical_id = (
                    override["canonical_spotify_id"]
                )

                canonical_matches = approved_candidates[
                    approved_candidates["spotify_id"]
                    == canonical_id
                ]

                if canonical_matches.empty:
                    canonical_id = choose_canonical_candidate(
                        [
                            {
                                "spotify_id": row["spotify_id"],
                                "play_count": row["play_count"],
                                "last_played": row["last_played"],
                            }
                            for _, row
                            in approved_candidates.iterrows()
                        ]
                    )

                canonical_matches = approved_candidates[
                    approved_candidates["spotify_id"]
                    == canonical_id
                ]

                canonical_candidate = (
                    canonical_matches.iloc[0]
                )

                results.append({
                    "liked_spotify_id": liked_id,
                    "liked_track_name": liked_row["track_name"],
                    "liked_artist_name": liked_row["artist_name"],
                    "liked_album_name": liked_row["album_name"],
                    "liked_duration_ms": liked_row["duration_ms"],

                    "warehouse_spotify_id": canonical_id,
                    "warehouse_track_name": (
                        canonical_candidate["track_name"]
                    ),
                    "warehouse_artist_name": (
                        canonical_candidate["artist_name"]
                    ),
                    "warehouse_album_name": (
                        canonical_candidate["album_name"]
                    ),
                    "warehouse_duration_ms": (
                        canonical_candidate["duration_ms"]
                    ),

                    "warehouse_play_count": (
                        canonical_candidate["play_count"]
                    ),
                    "first_played": (
                        approved_candidates["first_played"]
                        .min()
                    ),
                    "last_played": (
                        approved_candidates["last_played"]
                        .max()
                    ),

                    "identity_status": "APPROVED MATCH",
                    "match_method": "MANUAL OVERRIDE",
                    "match_reason": override["reason"],

                    "title_similarity": None,
                    "duration_difference_ms": None,
                    "shared_artists": None,

                    "candidate_count": len(
                        approved_candidates
                    ),

                    "candidate_spotify_ids": " | ".join(
                        sorted(approved_ids)
                    ),

                    "canonical_spotify_id": canonical_id,
                    "canonical_play_count": (
                        canonical_candidate["play_count"]
                    ),

                    "review_required": False,
                })

                continue

        # -----------------------------------------------------------
        # Find non-ID candidates
        # -----------------------------------------------------------

        candidate_indexes = find_candidates(
            liked_row,
            warehouse_df,
            exact_index,
            base_index,
            compact_index,
        )

        evaluated_candidates = []

        for index in candidate_indexes:

            warehouse_row = warehouse_df.loc[index]

            evaluation = evaluate_candidate(
                liked_row,
                warehouse_row,
            )

            if evaluation is None:
                continue

            candidate = {
                "spotify_id": warehouse_row["spotify_id"],
                "track_name": warehouse_row["track_name"],
                "artist_name": warehouse_row["artist_name"],
                "album_name": warehouse_row["album_name"],
                "duration_ms": warehouse_row["duration_ms"],
                "play_count": warehouse_row["play_count"],
                "first_played": warehouse_row["first_played"],
                "last_played": warehouse_row["last_played"],
                **evaluation,
            }

            evaluated_candidates.append(
                candidate
            )

        # -----------------------------------------------------------
        # No candidates
        # -----------------------------------------------------------

        if not evaluated_candidates:

            results.append({
                "liked_spotify_id": liked_id,
                "liked_track_name": liked_row["track_name"],
                "liked_artist_name": liked_row["artist_name"],
                "liked_album_name": liked_row["album_name"],
                "liked_duration_ms": liked_row["duration_ms"],

                "warehouse_spotify_id": None,
                "warehouse_track_name": None,
                "warehouse_artist_name": None,
                "warehouse_album_name": None,
                "warehouse_duration_ms": None,

                "warehouse_play_count": 0,
                "first_played": None,
                "last_played": None,

                "identity_status": "UNMATCHED",
                "match_method": "NO CANDIDATES",
                "match_reason": (
                    "No warehouse candidate satisfied the title "
                    "and artist identity rules."
                ),

                "title_similarity": None,
                "duration_difference_ms": None,
                "shared_artists": None,

                "candidate_count": 0,
                "candidate_spotify_ids": None,

                "canonical_spotify_id": None,
                "canonical_play_count": 0,

                "review_required": True,
            })

            continue

        # -----------------------------------------------------------
        # Determine strongest candidate group
        # -----------------------------------------------------------

        strong_candidates = [
            c
            for c in evaluated_candidates
            if c["status"] == "STRONG MATCH"
        ]

        review_candidates = [
            c
            for c in evaluated_candidates
            if c["status"] == "REVIEW"
        ]

        # -----------------------------------------------------------
        # Strong identity candidates exist
        # -----------------------------------------------------------

        if strong_candidates:

            # All strong candidates represent the same identity when
            # they agree on the liked song's normalized/base identity.
            #
            # We do NOT call multiple Spotify IDs ambiguous anymore.
            canonical_id = choose_canonical_candidate(
                strong_candidates
            )

            canonical_candidate = next(
                c
                for c in strong_candidates
                if c["spotify_id"] == canonical_id
            )

            candidate_ids = sorted(
                {
                    c["spotify_id"]
                    for c in strong_candidates
                }
            )

            methods = sorted(
                {
                    c["method"]
                    for c in strong_candidates
                }
            )

            shared_artist_values = sorted(
                {
                    artist
                    for c in strong_candidates
                    for artist in c["shared_artists"]
                }
            )

            # If there are additional review candidates that are
            # clearly unrelated, they are not allowed to contaminate
            # the strong identity group.
            #
            # We report them separately so the CSV remains auditable.

            results.append({
                "liked_spotify_id": liked_id,
                "liked_track_name": liked_row["track_name"],
                "liked_artist_name": liked_row["artist_name"],
                "liked_album_name": liked_row["album_name"],
                "liked_duration_ms": liked_row["duration_ms"],

                "warehouse_spotify_id": canonical_id,
                "warehouse_track_name": canonical_candidate["track_name"],
                "warehouse_artist_name": canonical_candidate["artist_name"],
                "warehouse_album_name": canonical_candidate["album_name"],
                "warehouse_duration_ms": canonical_candidate["duration_ms"],

                "warehouse_play_count": canonical_candidate["play_count"],
                "first_played": canonical_candidate["first_played"],
                "last_played": canonical_candidate["last_played"],

                "identity_status": "STRONG MATCH",
                "match_method": " | ".join(methods),
                "match_reason": (
                    f"{len(strong_candidates)} Spotify ID(s) resolve "
                    f"to the same song identity. Canonical version "
                    f"selected by listening history."
                ),

                "title_similarity": max(
                    c["title_similarity"]
                    for c in strong_candidates
                ),

                "duration_difference_ms": min(
                    c["duration_difference_ms"]
                    for c in strong_candidates
                    if c["duration_difference_ms"] is not None
                )
                if any(
                    c["duration_difference_ms"] is not None
                    for c in strong_candidates
                )
                else None,

                "shared_artists": ", ".join(
                    shared_artist_values
                ),

                "candidate_count": len(
                    strong_candidates
                ),

                "candidate_spotify_ids": " | ".join(
                    candidate_ids
                ),

                "canonical_spotify_id": canonical_id,
                "canonical_play_count": canonical_candidate["play_count"],

                "review_required": False,
            })

            continue

        # -----------------------------------------------------------
        # Review candidates only
        # -----------------------------------------------------------

        # Pick the strongest review candidate for display, but keep
        # every candidate ID so the row can be investigated manually.

        review_candidates.sort(
            key=lambda c: (
                -c["title_similarity"],
                c["duration_difference_ms"]
                if c["duration_difference_ms"] is not None
                else float("inf"),
                -float(c["play_count"] or 0),
            )
        )

        best = review_candidates[0]

        candidate_ids = sorted(
            {
                c["spotify_id"]
                for c in review_candidates
            }
        )

        results.append({
            "liked_spotify_id": liked_id,
            "liked_track_name": liked_row["track_name"],
            "liked_artist_name": liked_row["artist_name"],
            "liked_album_name": liked_row["album_name"],
            "liked_duration_ms": liked_row["duration_ms"],

            "warehouse_spotify_id": best["spotify_id"],
            "warehouse_track_name": best["track_name"],
            "warehouse_artist_name": best["artist_name"],
            "warehouse_album_name": best["album_name"],
            "warehouse_duration_ms": best["duration_ms"],

            "warehouse_play_count": best["play_count"],
            "first_played": best["first_played"],
            "last_played": best["last_played"],

            "identity_status": "REVIEW",
            "match_method": best["method"],
            "match_reason": (
                f"Human review required. "
                f"{len(review_candidates)} candidate(s) found."
            ),

            "title_similarity": best["title_similarity"],
            "duration_difference_ms": best["duration_difference_ms"],

            "shared_artists": ", ".join(
                sorted(best["shared_artists"])
            ),

            "candidate_count": len(
                review_candidates
            ),

            "candidate_spotify_ids": " | ".join(
                candidate_ids
            ),

            "canonical_spotify_id": None,
            "canonical_play_count": None,

            "review_required": True,
        })

    # ---------------------------------------------------------------
    # Build output
    # ---------------------------------------------------------------

    review_df = pd.DataFrame(results)

    review_df = review_df.sort_values(
        by=[
            "identity_status",
            "liked_track_name",
            "liked_artist_name",
        ],
        kind="stable",
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    review_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print("Identity review created:")
    print(OUTPUT_FILE)
    print()

    print("=" * 60)
    print("SONG IDENTITY RESULTS")
    print("=" * 60)

    print(
        f"\nLiked Spotify IDs: "
        f"{len(liked_df):,}"
    )

    status_counts = (
        review_df["identity_status"]
        .value_counts()
    )

    for status in [
        "EXACT MATCH",
        "APPROVED MATCH",
        "STRONG MATCH",
        "REVIEW",
        "UNMATCHED",
    ]:

        print(
            f"{status:<35}"
            f"{status_counts.get(status, 0):>6,}"
        )

    print()
    print("MATCH METHODS")
    print("-" * 60)

    method_counts = (
        review_df["match_method"]
        .value_counts()
    )

    for method, count in method_counts.items():
        print(
            f"{method:<55}"
            f"{count:>6,}"
        )

    strong_with_multiple = review_df[
        (
            review_df["identity_status"]
            == "STRONG MATCH"
        )
        &
        (
            review_df["candidate_count"]
            > 1
        )
    ]

    print()
    print(
        "Strong identities with multiple Spotify IDs: "
        f"{len(strong_with_multiple):,}"
    )

    print()
    print("Database changes made:         0")
    print("Spotify changes made:          0")
    print()
    print("This was a READ-ONLY identity investigation.")
    print("=" * 60)


if __name__ == "__main__":
    main()