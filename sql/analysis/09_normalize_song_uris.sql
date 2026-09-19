-- ============================================================
-- 09_normalize_song_uris.sql
-- Build canonical Spotify URI compatibility mapping
--
-- The permanent song_identity_map is now the authoritative
-- source for Spotify song identity.
--
-- This script NO LONGER determines which Spotify IDs represent
-- the same song.
--
-- Its job is to:
--   1. Rebuild canonical_song_uris from song_identity_map.
--   2. Preserve the existing downstream compatibility table.
--   3. Update listening_history_warehouse.spotify_uri to the
--      canonical URI assigned by song_identity_map.
-- ============================================================


-- ------------------------------------------------------------
-- 1. Rebuild canonical song mapping
--
-- song_identity_map contains one row for every Spotify ID
-- found in either liked_songs or listening_history_warehouse.
--
-- Each resolved Spotify ID points to its canonical Spotify ID.
--
-- UNMATCHED liked-only songs have NULL canonical_spotify_id
-- and therefore do not appear in this compatibility table.
-- ------------------------------------------------------------

DROP TABLE IF EXISTS canonical_song_uris;


CREATE TABLE canonical_song_uris AS

SELECT
    spotify_id,

    CONCAT(
        'spotify:track:',
        canonical_spotify_id
    ) AS canonical_uri,

    COUNT(*) OVER (
        PARTITION BY canonical_spotify_id
    ) AS version_count

FROM song_identity_map

WHERE canonical_spotify_id IS NOT NULL;


-- ------------------------------------------------------------
-- 3. Index canonical mapping
--
-- This is critical because the warehouse has ~800k rows.
-- ------------------------------------------------------------

ALTER TABLE canonical_song_uris
ADD INDEX idx_canonical_song_uris_spotify_id (spotify_id);


-- ------------------------------------------------------------
-- 4. Update warehouse to canonical URIs
--
-- The identity map has already decided which Spotify ID is
-- canonical. This simply applies that decision.
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
-- 5. Verification
--
-- Expected result: 0
-- ------------------------------------------------------------

SELECT
    COUNT(*) AS remaining_mismatches

FROM listening_history_warehouse AS w

JOIN canonical_song_uris AS c
    ON w.spotify_id = c.spotify_id

WHERE w.spotify_uri <> c.canonical_uri;


-- ------------------------------------------------------------
-- 6. Verify Spotify IDs are unique in canonical mapping
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