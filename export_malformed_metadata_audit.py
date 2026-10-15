
from pathlib import Path

import pandas as pd

from audit_malformed_metadata import OUTPUT_FILE


def main():
    source = Path(OUTPUT_FILE)
    output = Path("malformed_metadata_candidate_audit.csv")

    if not source.exists():
        raise FileNotFoundError(
            f"Audit CSV not found: {source.resolve()}\n"
            "Run audit_malformed_metadata.py first."
        )

    df = pd.read_csv(source, dtype={"original_id": "string",
                                    "candidate_id": "string"})

    required_columns = [
        "original_id",
        "original_track_name",
        "original_artist_name",
        "play_count",
        "min_ms_played",
        "max_ms_played",
        "distinct_play_durations",
        "search_type",
        "candidate_id",
        "candidate_name",
        "candidate_artists",
        "title_match",
        "artist_match",
        "album",
        "release_date",
        "duration_ms",
        "duration_minus_longest_play_ms",
        "is_playable",
        "candidate_uri",
        "candidate_url",
    ]

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(
            "The source audit is missing required columns: "
            + ", ".join(missing)
        )

    # Keep every candidate row and all original audit fields.
    # Do not deduplicate candidates or discard uncertain matches.
    df = df[required_columns].copy()

    # Preserve Spotify IDs as text and normalize boolean fields.
    for column in ("original_id", "candidate_id"):
        df[column] = df[column].fillna("").astype(str)

    df.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Exported {len(df)} candidate rows.")
    print(f"Distinct original tracks: {df['original_id'].nunique()}")
    print(f"Output: {output.resolve()}")


if __name__ == "__main__":
    main()
