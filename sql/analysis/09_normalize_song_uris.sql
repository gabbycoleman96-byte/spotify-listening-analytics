-- ============================================================
-- 09_normalize_song_uris.sql
-- Canonicalize Spotify track URIs
--
-- Option A:
-- Treat Spotify track IDs with the same normalized
-- track name + artist name as versions of the same song.
--
-- Canonical version priority:
--   1. Liked version
--   2. Most-played version
--   3. Lowest Spotify ID as deterministic tie-breaker
-- ============================================================


-- ------------------------------------------------------------
-- 1. Rebuild canonical song mapping
-- ------------------------------------------------------------

DROP TABLE IF EXISTS canonical_song_uris;


CREATE TABLE canonical_song_uris AS

WITH song_versions AS (

    SELECT
        spotify_id,

        LOWER(
            REGEXP_REPLACE(
                TRIM(track_name),
                '[[:space:]]+',
                ' '
            )
        ) AS normalized_track_name,

        LOWER(
            REGEXP_REPLACE(
                TRIM(artist_name),
                '[[:space:]]+',
                ' '
            )
        ) AS normalized_artist_name,

        MAX(is_liked) AS is_liked,
        COUNT(*) AS play_count

    FROM listening_history_warehouse

    WHERE spotify_id IS NOT NULL
      AND track_name IS NOT NULL
      AND artist_name IS NOT NULL

    GROUP BY
        spotify_id,
        LOWER(
            REGEXP_REPLACE(
                TRIM(track_name),
                '[[:space:]]+',
                ' '
            )
        ),
        LOWER(
            REGEXP_REPLACE(
                TRIM(artist_name),
                '[[:space:]]+',
                ' '
            )
        )
),

ranked_versions AS (

    SELECT
        spotify_id,
        normalized_track_name,
        normalized_artist_name,
        is_liked,
        play_count,

        ROW_NUMBER() OVER (
            PARTITION BY
                normalized_track_name,
                normalized_artist_name

            ORDER BY
                is_liked DESC,
                play_count DESC,
                spotify_id
        ) AS canonical_rank,

        COUNT(*) OVER (
            PARTITION BY
                normalized_track_name,
                normalized_artist_name
        ) AS version_count

    FROM song_versions
)

SELECT
    spotify_id,

    CONCAT(
        'spotify:track:',
        FIRST_VALUE(spotify_id) OVER (
            PARTITION BY
                normalized_track_name,
                normalized_artist_name

            ORDER BY
                canonical_rank
        )
    ) AS canonical_uri,

    version_count

FROM ranked_versions;


-- ------------------------------------------------------------
-- 2. Index canonical mapping
--
-- This is critical because the warehouse has ~800k rows.
-- ------------------------------------------------------------

ALTER TABLE canonical_song_uris
ADD INDEX idx_canonical_song_uris_spotify_id (spotify_id);


-- ------------------------------------------------------------
-- 3. Update warehouse to canonical URIs
--
-- Only rows that actually need changing are touched.
-- ------------------------------------------------------------

UPDATE listening_history_warehouse AS w

JOIN canonical_song_uris AS c
    ON w.spotify_id = c.spotify_id

SET
    w.spotify_uri = c.canonical_uri

WHERE w.spotify_uri <> c.canonical_uri;


-- ------------------------------------------------------------
-- 4. Verification
--
-- Expected result: 0
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS remaining_mismatches

FROM listening_history_warehouse AS w

JOIN canonical_song_uris AS c
    ON w.spotify_id = c.spotify_id

WHERE w.spotify_uri <> c.canonical_uri;