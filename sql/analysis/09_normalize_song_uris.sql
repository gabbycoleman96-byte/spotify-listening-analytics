-- ============================================================
-- 09_normalize_song_uris.sql
-- Canonicalize Spotify track URIs
--
-- Option A:
-- Treat Spotify track IDs with the same normalized
-- track name + artist name as versions of the same song.
--
-- Spotify ID identity rule:
--   Each Spotify ID represents one track.
--
-- If Spotify metadata changes over time for the same Spotify ID,
-- use the track/artist representation from its MOST RECENT play.
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

WITH latest_version AS (

    -- --------------------------------------------------------
    -- Get exactly ONE metadata representation per Spotify ID.
    --
    -- The most recent listening event is treated as the most
    -- current Spotify-accurate representation we have seen.
    -- --------------------------------------------------------

    SELECT
        spotify_id,
        track_name,
        artist_name

    FROM (

        SELECT
            h.spotify_id,
            h.track_name,
            h.artist_name,

            ROW_NUMBER() OVER (
                PARTITION BY h.spotify_id
                ORDER BY h.played_at DESC
            ) AS latest_rank

        FROM listening_history_warehouse h

        WHERE h.spotify_id IS NOT NULL
          AND h.track_name IS NOT NULL
          AND h.artist_name IS NOT NULL

    ) latest

    WHERE latest_rank = 1
),


play_counts AS (

    -- --------------------------------------------------------
    -- Calculate total listening history for each Spotify ID.
    -- --------------------------------------------------------

    SELECT
        spotify_id,
        COUNT(*) AS play_count

    FROM listening_history_warehouse

    WHERE spotify_id IS NOT NULL

    GROUP BY
        spotify_id
),


song_versions AS (

    -- --------------------------------------------------------
    -- Combine the latest representation with play counts and
    -- current liked status.
    --
    -- Because latest_version contains exactly one row per
    -- Spotify ID, each Spotify ID can now appear only once.
    -- --------------------------------------------------------

    SELECT
        v.spotify_id,

        LOWER(
            REGEXP_REPLACE(
                TRIM(v.track_name),
                '[[:space:]]+',
                ' '
            )
        ) AS normalized_track_name,

        LOWER(
            REGEXP_REPLACE(
                TRIM(v.artist_name),
                '[[:space:]]+',
                ' '
            )
        ) AS normalized_artist_name,

        MAX(
            CASE
                WHEN l.spotify_id IS NOT NULL THEN 1
                ELSE 0
            END
        ) AS is_liked,

        p.play_count

    FROM latest_version v

    JOIN play_counts p
        ON v.spotify_id = p.spotify_id

    LEFT JOIN liked_songs l
        ON v.spotify_id = l.spotify_id

    GROUP BY
        v.spotify_id,
        v.track_name,
        v.artist_name,
        p.play_count
),


ranked_versions AS (

    -- --------------------------------------------------------
    -- Rank Spotify versions within each normalized song.
    -- --------------------------------------------------------

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
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS remaining_mismatches

FROM listening_history_warehouse AS w

JOIN canonical_song_uris AS c
    ON w.spotify_id = c.spotify_id

WHERE w.spotify_uri <> c.canonical_uri;


-- ------------------------------------------------------------
-- 5. Verify Spotify IDs are unique in canonical mapping
--
-- Expected result: 0
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS duplicate_spotify_ids

FROM (
    SELECT
        spotify_id

    FROM canonical_song_uris

    GROUP BY
        spotify_id

    HAVING COUNT(*) > 1
) duplicates;