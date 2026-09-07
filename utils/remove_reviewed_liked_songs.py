"""
remove_reviewed_liked_songs.py

Purpose
-------
Execute the user's manually reviewed liked-song cleanup decisions.

This utility reads:
    data/manual/liked_songs _cleanup_reviewed.csv

Only records with:
    final_action = REMOVE

are eligible for deletion.

Safety
------
- Dry-run by default.
- Spotify deletion requires --execute.
- Expected REMOVE count is validated.
- Spotify IDs are validated.
- Duplicate Spotify IDs are rejected.
- MySQL is updated only after Spotify accepts a batch.
- The archive table is NEVER modified.
"""

# ============================================================
# Imports
# ============================================================

import argparse
from pathlib import Path

import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sqlalchemy import text

from load.database import engine


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REVIEW_FILE = (
    PROJECT_ROOT
    / "data"
    / "manual"
    / "liked_songs _cleanup_reviewed.csv"
)

EXPECTED_REMOVE_COUNT = 615

BATCH_SIZE = 40

SPOTIFY_SCOPE = (
    "user-library-read "
    "user-library-modify"
)


# ============================================================
# Spotify Client
# ============================================================

def create_spotify_client():
    """
    Create a Spotify client with both read and library-modify
    permissions.
    """

    import os

    from dotenv import load_dotenv

    load_dotenv()

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope=SPOTIFY_SCOPE,
        )
    )


# ============================================================
# Load reviewed decisions
# ============================================================

def load_reviewed_removals():
    """
    Load the reviewed CSV and return only explicit REMOVE records.
    """

    if not REVIEW_FILE.exists():

        raise FileNotFoundError(
            f"""
Reviewed cleanup file was not found:

{REVIEW_FILE}

Make sure the reviewed CSV is in:
data/manual/
"""
        )

    df = pd.read_csv(REVIEW_FILE)

    required_columns = {
        "spotify_id",
        "track_name",
        "artist_name",
        "album_name",
        "final_action",
    }

    missing_columns = (
        required_columns
        - set(df.columns)
    )

    if missing_columns:

        raise ValueError(
            "Reviewed CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    # --------------------------------------------------------
    # Validate final_action values
    # --------------------------------------------------------

    allowed_actions = {
        "KEEP",
        "REMOVE",
        "ALREADY REMOVED",
    }

    unexpected_actions = set(
        df["final_action"]
        .dropna()
        .astype(str)
        .str.strip()
    ) - allowed_actions

    if unexpected_actions:

        raise ValueError(
            "Unexpected final_action values found: "
            + ", ".join(sorted(unexpected_actions))
        )

    # --------------------------------------------------------
    # Select only explicit REMOVE decisions
    # --------------------------------------------------------

    remove_df = df[
        df["final_action"]
        .astype(str)
        .str.strip()
        .eq("REMOVE")
    ].copy()

    print(
        f"Reviewed records loaded:       {len(df):,}"
    )

    print(
        f"Explicit REMOVE decisions:     {len(remove_df):,}"
    )

    # --------------------------------------------------------
    # Validate expected count
    # --------------------------------------------------------

    if len(remove_df) != EXPECTED_REMOVE_COUNT:

        raise ValueError(
            f"""
REMOVE count validation failed.

Expected:
    {EXPECTED_REMOVE_COUNT:,}

Found:
    {len(remove_df):,}

No changes will be made.
"""
        )

    # --------------------------------------------------------
    # Validate Spotify IDs
    # --------------------------------------------------------

    missing_ids = (
        remove_df["spotify_id"]
        .isna()
        | remove_df["spotify_id"]
        .astype(str)
        .str.strip()
        .eq("")
    )

    if missing_ids.any():

        bad_count = int(missing_ids.sum())

        raise ValueError(
            f"""
{bad_count} REMOVE records do not have a Spotify ID.

No changes will be made.
"""
        )

    remove_df["spotify_id"] = (
        remove_df["spotify_id"]
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Validate duplicate Spotify IDs
    # --------------------------------------------------------

    duplicate_ids = (
        remove_df[
            remove_df["spotify_id"].duplicated(
                keep=False
            )
        ]
        ["spotify_id"]
        .unique()
        .tolist()
    )

    if duplicate_ids:

        raise ValueError(
            f"""
Duplicate Spotify IDs found in REMOVE list.

Duplicate ID count:
    {len(duplicate_ids):,}

No changes will be made.
"""
        )

    return remove_df


# ============================================================
# Print removal list summary
# ============================================================

def print_removal_summary(remove_df):
    """
    Print a concise summary before deletion.
    """

    print()
    print("=" * 70)
    print("REVIEWED SPOTIFY CLEANUP")
    print("=" * 70)

    print(
        f"Songs selected for removal: {len(remove_df):,}"
    )

    print()

    print(
        "These are the songs whose final_action column "
        "explicitly says REMOVE."
    )

    print()

    # Show a preview rather than dumping all 615 rows.
    preview = remove_df[
        [
            "track_name",
            "artist_name",
            "album_name",
            "spotify_id",
        ]
    ].head(10)

    print(preview.to_string(index=False))

    if len(remove_df) > 10:

        print()
        print(
            f"... plus {len(remove_df) - 10:,} more."
        )

    print()
    print("=" * 70)


# ============================================================
# Delete one Spotify batch
# ============================================================

def delete_spotify_batch(
    sp,
    spotify_ids
):
    """
    Remove one batch of Spotify tracks from the user's library.

    Spotify accepts a maximum of 40 track URIs/IDs per request.
    """

    sp.current_user_saved_tracks_delete(
        tracks=spotify_ids
    )


# ============================================================
# Update MySQL
# ============================================================

def delete_from_database(
    spotify_ids
):
    """
    Remove successfully deleted Spotify IDs from the live
    liked_songs table.

    The archive table is intentionally never referenced.
    """

    query = text(
        """
        DELETE FROM liked_songs
        WHERE spotify_id = :spotify_id
        """
    )

    with engine.begin() as connection:

        for spotify_id in spotify_ids:

            connection.execute(
                query,
                {
                    "spotify_id": spotify_id
                }
            )


# ============================================================
# Execute cleanup
# ============================================================

def execute_cleanup(
    remove_df,
    sp
):
    """
    Delete reviewed songs from Spotify and then MySQL.

    Each batch is committed to the database only after Spotify
    accepts the deletion request.
    """

    spotify_ids = (
        remove_df["spotify_id"]
        .tolist()
    )

    total = len(spotify_ids)

    spotify_deleted = 0
    database_deleted = 0

    print()
    print("=" * 70)
    print("STARTING SPOTIFY CLEANUP")
    print("=" * 70)
    print()

    for start in range(
        0,
        total,
        BATCH_SIZE
    ):

        batch = spotify_ids[
            start:start + BATCH_SIZE
        ]

        batch_number = (
            start // BATCH_SIZE
        ) + 1

        total_batches = (
            (total + BATCH_SIZE - 1)
            // BATCH_SIZE
        )

        print(
            f"Batch {batch_number}/{total_batches}: "
            f"{len(batch)} songs"
        )

        # ----------------------------------------------------
        # Spotify
        # ----------------------------------------------------

        try:

            delete_spotify_batch(
                sp,
                batch
            )

            print(
                "  Spotify: deletion accepted"
            )

        except Exception as e:

            print()
            print(
                "  Spotify deletion FAILED."
            )

            print(
                f"  Error: {e}"
            )

            print()
            print(
                "Stopping immediately."
            )

            print(
                f"Spotify batches completed: "
                f"{batch_number - 1}"
            )

            print(
                f"Spotify songs deleted: "
                f"{spotify_deleted:,}"
            )

            print(
                f"Database songs deleted: "
                f"{database_deleted:,}"
            )

            raise

        spotify_deleted += len(batch)

        # ----------------------------------------------------
        # MySQL
        # ----------------------------------------------------

        try:

            delete_from_database(
                batch
            )

            print(
                "  MySQL: live liked_songs updated"
            )

        except Exception as e:

            print()
            print(
                "  DATABASE UPDATE FAILED."
            )

            print(
                f"  Error: {e}"
            )

            print()
            print(
                "Spotify has accepted this batch, "
                "but MySQL did not update."
            )

            print(
                "Stopping immediately so the mismatch "
                "can be handled safely."
            )

            raise

        database_deleted += len(batch)

        print()

    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)

    print(
        f"Spotify songs deleted:  "
        f"{spotify_deleted:,}"
    )

    print(
        f"MySQL rows deleted:     "
        f"{database_deleted:,}"
    )

    print()
    print(
        "Archive table was not modified."
    )

    print("=" * 70)


# ============================================================
# Dry Run
# ============================================================

def dry_run(remove_df):
    """
    Validate the removal list without changing anything.
    """

    print()
    print("=" * 70)
    print("DRY RUN")
    print("=" * 70)

    print(
        f"Validated REMOVE records: "
        f"{len(remove_df):,}"
    )

    print()
    print(
        "No Spotify changes made."
    )

    print(
        "No database changes made."
    )

    print()
    print(
        "To actually execute the cleanup, run:"
    )

    print()
    print(
        "python -m utils.remove_reviewed_liked_songs --execute"
    )

    print()
    print("=" * 70)


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Execute manually reviewed Spotify "
            "Liked Songs cleanup."
        )
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Actually delete REMOVE records from "
            "Spotify and MySQL."
        ),
    )

    args = parser.parse_args()

    print()
    print("=" * 70)
    print("LIKED SONG CLEANUP EXECUTION")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # Load and validate
    # --------------------------------------------------------

    remove_df = load_reviewed_removals()

    print_removal_summary(
        remove_df
    )

    # --------------------------------------------------------
    # Dry run unless explicitly requested
    # --------------------------------------------------------

    if not args.execute:

        dry_run(
            remove_df
        )

        return

    # --------------------------------------------------------
    # Explicit execution
    # --------------------------------------------------------

    print()
    print(
        "WARNING: This will remove "
        f"{len(remove_df):,} songs from Spotify."
    )

    print(
        "The operation cannot be undone by this script."
    )

    print()

    confirmation = input(
        "Type DELETE 615 to continue: "
    ).strip()

    if confirmation != "DELETE 615":

        print()
        print(
            "Confirmation did not match."
        )

        print(
            "No changes were made."
        )

        return

    # --------------------------------------------------------
    # Create Spotify client
    # --------------------------------------------------------

    print()
    print(
        "Authenticating with Spotify..."
    )

    sp = create_spotify_client()

    print(
        "Spotify authentication successful."
    )

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    execute_cleanup(
        remove_df,
        sp
    )


if __name__ == "__main__":
    main()