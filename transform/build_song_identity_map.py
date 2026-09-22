"""
Build the permanent Spotify song identity map.

This script consumes the accepted, read-only identity investigation output
and creates the MySQL table:

    song_identity_map

Run from the project root:

    python -m transform.build_song_identity_map

The script does NOT rerun identity matching. It uses the decisions already
stored in:

    data/investigative/song_identity_review.csv

The new table is built and validated before replacing an existing
song_identity_map table.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load.database import engine


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REVIEW_FILE = (
    PROJECT_ROOT
    / "data"
    / "investigative"
    / "song_identity_review.csv"
)

SCHEMA_FILE = (
    PROJECT_ROOT
    / "sql"
    / "schema"
    / "06_song_identity_map.sql"
)

FINAL_TABLE = "song_identity_map"
BUILD_TABLE = "song_identity_map_build"


# ---------------------------------------------------------------------------
# Simple union-find
# ---------------------------------------------------------------------------

class DisjointSet:
    """
    Groups Spotify IDs into connected identity components.

    If:

        A -> B
        A -> C

    then A, B, and C become one identity component.
    """

    def __init__(self):
        self.parent = {}

    def add(self, value):
        if value not in self.parent:
            self.parent[value] = value

    def find(self, value):
        self.add(value)

        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])

        return self.parent[value]

    def union(self, left, right):
        left_root = self.find(left)
        right_root = self.find(right)

        if left_root != right_root:
            self.parent[right_root] = left_root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def split_candidate_ids(value) -> list[str]:
    """Convert the pipe-separated candidate ID field into a list."""

    if pd.isna(value) or not str(value).strip():
        return []

    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


def load_review() -> pd.DataFrame:
    """Load the accepted identity investigation."""

    if not REVIEW_FILE.exists():
        raise FileNotFoundError(
            f"Identity investigation file not found:\n{REVIEW_FILE}"
        )

    review_df = pd.read_csv(
        REVIEW_FILE,
        dtype=str,
    )

    required_columns = {
        "liked_spotify_id",
        "identity_status",
        "match_method",
        "match_reason",
        "candidate_spotify_ids",
        "canonical_spotify_id",
    }

    missing = required_columns - set(review_df.columns)

    if missing:
        raise ValueError(
            "Identity investigation is missing required columns: "
            + ", ".join(sorted(missing))
        )

    return review_df


def load_spotify_id_sets():
    """Load the complete Spotify ID universe from liked songs and warehouse."""

    liked_df = pd.read_sql(
        text(
            """
            SELECT DISTINCT spotify_id
            FROM liked_songs
            WHERE spotify_id IS NOT NULL
            """
        ),
        engine,
    )

    warehouse_df = pd.read_sql(
        text(
            """
            SELECT DISTINCT spotify_id
            FROM listening_history_warehouse
            WHERE spotify_id IS NOT NULL
            """
        ),
        engine,
    )

    liked_ids = set(
        liked_df["spotify_id"].astype(str)
    )

    warehouse_ids = set(
        warehouse_df["spotify_id"].astype(str)
    )

    return liked_ids, warehouse_ids


def load_warehouse_play_counts() -> dict[str, int]:
    """Load total play counts for each warehouse Spotify ID."""

    warehouse_df = pd.read_sql(
        text(
            """
            SELECT
                spotify_id,
                COUNT(*) AS play_count
            FROM listening_history_warehouse
            WHERE spotify_id IS NOT NULL
            GROUP BY spotify_id
            """
        ),
        engine,
    )

    return {
        str(row["spotify_id"]): int(row["play_count"])
        for _, row in warehouse_df.iterrows()
    }


# ---------------------------------------------------------------------------
# Identity components
# ---------------------------------------------------------------------------

def build_components(review_df: pd.DataFrame):
    """
    Build connected identity groups from accepted investigation results.

    For each resolved liked song:

        liked Spotify ID <-> every accepted candidate Spotify ID

    This means all known Spotify versions belonging to one accepted identity
    end up in the same component.
    """

    dsu = DisjointSet()

    for _, row in review_df.iterrows():

        liked_id = str(
            row["liked_spotify_id"]
        )

        dsu.add(liked_id)

        candidate_ids = split_candidate_ids(
            row["candidate_spotify_ids"]
        )

        # Fallback for investigation files that may have a warehouse ID
        # but no populated candidate_spotify_ids field.
        if not candidate_ids:

            warehouse_id = row.get(
                "warehouse_spotify_id"
            )

            if pd.notna(warehouse_id):
                candidate_ids = [
                    str(warehouse_id)
                ]

        for candidate_id in candidate_ids:
            dsu.union(
                liked_id,
                candidate_id,
            )

    components = defaultdict(set)

    for spotify_id in dsu.parent:
        components[
            dsu.find(spotify_id)
        ].add(spotify_id)

    return components, dsu


def choose_component_canonical(
    canonical_candidates: set[str],
    play_counts: dict[str, int],
) -> str:
    """
    Choose the canonical Spotify ID for an identity component.

    Highest listening history wins.

    Spotify ID provides deterministic tie-breaking.
    """

    return max(
        canonical_candidates,
        key=lambda spotify_id: (
            play_counts.get(
                spotify_id,
                0,
            ),
            spotify_id,
        ),
    )


# ---------------------------------------------------------------------------
# Build mapping
# ---------------------------------------------------------------------------

def build_mapping(
    review_df: pd.DataFrame,
    liked_ids: set[str],
    warehouse_ids: set[str],
    play_counts: dict[str, int],
) -> pd.DataFrame:

    components, dsu = build_components(
        review_df
    )

    canonical_by_component = defaultdict(set)
    status_by_component = defaultdict(set)
    method_by_component = defaultdict(set)

    for _, row in review_df.iterrows():

        liked_id = str(
            row["liked_spotify_id"]
        )

        component = dsu.find(
            liked_id
        )

        canonical_id = row[
            "canonical_spotify_id"
        ]

        if (
            pd.notna(canonical_id)
            and str(canonical_id).strip()
        ):
            canonical_by_component[
                component
            ].add(
                str(canonical_id).strip()
            )

        status_by_component[
            component
        ].add(
            str(row["identity_status"])
        )

        if pd.notna(
            row["match_method"]
        ):
            method_by_component[
                component
            ].add(
                str(row["match_method"])
            )

    rows = []

    # -----------------------------------------------------------------------
    # Resolved identity components
    # -----------------------------------------------------------------------

    for component, spotify_ids in components.items():

        canonical_candidates = (
            canonical_by_component.get(
                component,
                set(),
            )
        )

        if canonical_candidates:

            canonical_id = (
                choose_component_canonical(
                    canonical_candidates,
                    play_counts,
                )
            )

            statuses = (
                status_by_component[
                    component
                ]
            )

            if "APPROVED MATCH" in statuses:

                resolution_status = (
                    "APPROVED MATCH"
                )

            elif "STRONG MATCH" in statuses:

                resolution_status = (
                    "STRONG MATCH"
                )

            else:

                resolution_status = (
                    "EXACT MATCH"
                )

            methods = sorted(
                method_by_component[
                    component
                ]
            )

            resolution_method = (
                " | ".join(methods)
            )

            resolution_reason = (
                "Accepted identity group from "
                "song identity investigation. "
                f"Canonical Spotify ID selected "
                f"by listening history: "
                f"{canonical_id}."
            )

            for spotify_id in spotify_ids:

                if (
                    spotify_id in liked_ids
                    and spotify_id in warehouse_ids
                ):
                    source_type = (
                        "LIKED_AND_WAREHOUSE"
                    )

                elif spotify_id in liked_ids:

                    source_type = (
                        "LIKED_ONLY"
                    )

                else:

                    source_type = (
                        "WAREHOUSE_ONLY"
                    )

                rows.append(
                    {
                        "spotify_id": spotify_id,
                        "canonical_spotify_id": canonical_id,
                        "resolution_status": resolution_status,
                        "resolution_method": resolution_method,
                        "resolution_reason": resolution_reason,
                        "is_liked": (
                            spotify_id in liked_ids
                        ),
                        "source_type": source_type,
                    }
                )

        else:

            # Unmatched liked song.
            for spotify_id in spotify_ids:

                if spotify_id not in liked_ids:
                    continue

                rows.append(
                    {
                        "spotify_id": spotify_id,
                        "canonical_spotify_id": None,
                        "resolution_status": "UNMATCHED",
                        "resolution_method": "NO CANDIDATES",
                        "resolution_reason": (
                            "No warehouse song passed "
                            "the accepted identity "
                            "candidate rules."
                        ),
                        "is_liked": True,
                        "source_type": "LIKED_ONLY",
                    }
                )
                
    # -----------------------------------------------------------------------
    # Newly liked IDs not present in the identity investigation
    # -----------------------------------------------------------------------

    mapped_ids = {
        row["spotify_id"]
        for row in rows
    }

    new_liked_ids = (
        liked_ids
        - mapped_ids
    )

    for spotify_id in sorted(new_liked_ids):

        if spotify_id in warehouse_ids:

            # Newly liked song that already exists in listening history.
            # No identity investigation was needed because the Spotify ID
            # itself is the exact identity present in the warehouse.

            rows.append(
                {
                    "spotify_id": spotify_id,
                    "canonical_spotify_id": spotify_id,
                    "resolution_status": "EXACT MATCH",
                    "resolution_method": "EXACT SPOTIFY ID",
                    "resolution_reason": (
                        "Liked song was added after the identity "
                        "investigation but the same Spotify ID already "
                        "exists in listening history."
                    ),
                    "is_liked": True,
                    "source_type": "LIKED_AND_WAREHOUSE",
                }
            )

        else:

            # Newly liked song with no listening history.
            # There is no evidence available to resolve it to another
            # Spotify ID, so leave it unmatched until it is played or
            # otherwise investigated.

            rows.append(
                {
                    "spotify_id": spotify_id,
                    "canonical_spotify_id": None,
                    "resolution_status": "UNMATCHED",
                    "resolution_method": "NO INVESTIGATION",
                    "resolution_reason": (
                        "Liked song was added after the identity "
                        "investigation and does not currently exist "
                        "in listening history."
                    ),
                    "is_liked": True,
                    "source_type": "LIKED_ONLY",
                }
            )            

    # -----------------------------------------------------------------------
    # Warehouse-only IDs
    # -----------------------------------------------------------------------

    mapped_ids = {
        row["spotify_id"]
        for row in rows
    }

    for spotify_id in sorted(
        warehouse_ids - mapped_ids
    ):

        rows.append(
            {
                "spotify_id": spotify_id,
                "canonical_spotify_id": spotify_id,
                "resolution_status": "WAREHOUSE ONLY",
                "resolution_method": "WAREHOUSE SELF",
                "resolution_reason": (
                    "Spotify ID exists in listening "
                    "history but was not part of a "
                    "liked-song identity group."
                ),
                "is_liked": False,
                "source_type": "WAREHOUSE_ONLY",
            }
        )

    mapping_df = pd.DataFrame(
        rows
    )

    if mapping_df.empty:
        raise ValueError(
            "No identity mappings were generated."
        )

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    if mapping_df[
        "spotify_id"
    ].duplicated().any():

        duplicates = (
            mapping_df.loc[
                mapping_df[
                    "spotify_id"
                ].duplicated(
                    keep=False
                ),
                "spotify_id",
            ]
            .drop_duplicates()
            .tolist()
        )

        raise ValueError(
            "Duplicate Spotify IDs generated "
            "in identity map: "
            + ", ".join(
                duplicates[:20]
            )
        )

    missing_liked = (
        liked_ids
        - set(mapping_df["spotify_id"])
    )

    if missing_liked:

        raise ValueError(
            "Identity map is missing liked "
            "Spotify IDs: "
            + ", ".join(
                sorted(missing_liked)[:20]
            )
        )

    missing_warehouse = (
        warehouse_ids
        - set(mapping_df["spotify_id"])
    )

    if missing_warehouse:

        raise ValueError(
            "Identity map is missing warehouse "
            "Spotify IDs: "
            + ", ".join(
                sorted(missing_warehouse)[:20]
            )
        )

    return (
        mapping_df
        .sort_values(
            by="spotify_id",
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def table_exists(
    connection,
    table_name: str,
) -> bool:

    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
            """
        ),
        {
            "table_name": table_name
        },
    )

    return result.scalar() > 0


def create_build_table(
    connection,
):
    """Create the temporary build table from the schema file."""

    schema_sql = SCHEMA_FILE.read_text(
        encoding="utf-8"
    )

    build_sql = schema_sql.replace(
        "CREATE TABLE song_identity_map",
        f"CREATE TABLE {BUILD_TABLE}",
        1,
    )

    connection.execute(
        text(build_sql)
    )


def insert_mapping(
    connection,
    mapping_df: pd.DataFrame,
):
    """Insert the generated identity map into the build table."""

    insert_sql = text(
        f"""
        INSERT INTO {BUILD_TABLE} (
            spotify_id,
            canonical_spotify_id,
            resolution_status,
            resolution_method,
            resolution_reason,
            is_liked,
            source_type
        )
        VALUES (
            :spotify_id,
            :canonical_spotify_id,
            :resolution_status,
            :resolution_method,
            :resolution_reason,
            :is_liked,
            :source_type
        )
        """
    )

    records = mapping_df[
        [
            "spotify_id",
            "canonical_spotify_id",
            "resolution_status",
            "resolution_method",
            "resolution_reason",
            "is_liked",
            "source_type",
        ]
    ].to_dict("records")

    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None

    connection.execute(
        insert_sql,
        records,
    )


def validate_build_table(
    connection,
    expected_count: int,
):
    """Validate the database build before swapping it into place."""

    actual_count = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {BUILD_TABLE}
            """
        )
    ).scalar()

    if actual_count != expected_count:

        raise RuntimeError(
            "Build table row count mismatch. "
            f"Expected {expected_count:,}, "
            f"got {actual_count:,}."
        )

    duplicate_count = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT spotify_id
                FROM {BUILD_TABLE}
                GROUP BY spotify_id
                HAVING COUNT(*) > 1
            ) duplicate_ids
            """
        )
    ).scalar()

    if duplicate_count:

        raise RuntimeError(
            "Build table contains "
            f"{duplicate_count} duplicate IDs."
        )

    missing_canonical_count = connection.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {BUILD_TABLE}
            WHERE resolution_status <> 'UNMATCHED'
              AND canonical_spotify_id IS NULL
            """
        )
    ).scalar()

    if missing_canonical_count:

        raise RuntimeError(
            "Resolved identities contain "
            "NULL canonical Spotify IDs."
        )


def swap_tables(
    connection,
):
    """
    Replace the existing table only after validation succeeds.

    Existing table is preserved under a timestamped backup name.
    """

    has_final = table_exists(
        connection,
        FINAL_TABLE,
    )

    if has_final:

        backup_name = (
            f"{FINAL_TABLE}_backup_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        connection.execute(
            text(
                f"""
                RENAME TABLE
                    {FINAL_TABLE} TO {backup_name},
                    {BUILD_TABLE} TO {FINAL_TABLE}
                """
            )
        )

        print(
            f"Previous table backed up as: "
            f"{backup_name}"
        )

    else:

        connection.execute(
            text(
                f"""
                RENAME TABLE
                    {BUILD_TABLE} TO {FINAL_TABLE}
                """
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    print("\n" + "=" * 60)
    print("BUILD SONG IDENTITY MAP")
    print("=" * 60)

    # -----------------------------------------------------------------------
    # Load accepted investigation
    # -----------------------------------------------------------------------

    review_df = load_review()

    print(
        f"Investigation rows:   {len(review_df):,}"
    )

    # -----------------------------------------------------------------------
    # Load ID universe
    # -----------------------------------------------------------------------

    liked_ids, warehouse_ids = (
        load_spotify_id_sets()
    )

    print(
        f"Liked Spotify IDs:     {len(liked_ids):,}"
    )

    print(
        f"Warehouse Spotify IDs: {len(warehouse_ids):,}"
    )

    # -----------------------------------------------------------------------
    # Load play counts
    # -----------------------------------------------------------------------

    play_counts = load_warehouse_play_counts()

    # -----------------------------------------------------------------------
    # Build mapping
    # -----------------------------------------------------------------------

    print("\nBuilding identity map...")

    mapping_df = build_mapping(
        review_df,
        liked_ids,
        warehouse_ids,
        play_counts,
    )

    print(
        f"Identity map rows:     {len(mapping_df):,}"
    )

    # -----------------------------------------------------------------------
    # Resolution summary
    # -----------------------------------------------------------------------

    print("\nResolution status:")

    resolution_counts = (
        mapping_df["resolution_status"]
        .value_counts()
    )

    for status, count in resolution_counts.items():
        print(
            f"  {status:<20} {count:>8,}"
        )

    print("\nSource type:")

    source_counts = (
        mapping_df["source_type"]
        .value_counts()
    )

    for source_type, count in source_counts.items():
        print(
            f"  {source_type:<20} {count:>8,}"
        )

    # -----------------------------------------------------------------------
    # Database build
    # -----------------------------------------------------------------------

    print("\nCreating validated build table...")

    with engine.begin() as connection:

        connection.execute(
            text(
                f"""
                DROP TABLE IF EXISTS
                    {BUILD_TABLE}
                """
            )
        )

        create_build_table(
            connection
        )

        insert_mapping(
            connection,
            mapping_df,
        )

        validate_build_table(
            connection,
            len(mapping_df),
        )

        swap_tables(
            connection
        )

    print("\n" + "=" * 60)
    print("SONG IDENTITY MAP COMPLETE")
    print("=" * 60)

    print(
        f"Table: {FINAL_TABLE}"
    )

    print(
        f"Rows:  {len(mapping_df):,}"
    )

    print(
        "\nPermanent identity map is ready for "
        "downstream ETL and analytics."
    )