/*
08_album_listening_sequences.sql

Purpose
-------
Identify complete album listens from the listening warehouse.

Definition
----------
A qualifying album sequence:

1. Begins with album track 1.
2. Contains every track on the album.
3. Follows the canonical album order.
4. Contains no non-album track between album tracks.
5. Contains no repeated album track.
6. Uses only albums whose Spotify metadata is complete.

Grain
-----
One row = one complete, consecutive album-listening sequence.

The same album may therefore appear multiple times if it was
listened to completely more than once.
*/


-- ============================================================
-- Clear previous results
-- ============================================================

TRUNCATE TABLE album_listening_sequences;


-- ============================================================
-- Build complete canonical album track lists
-- ============================================================

INSERT INTO album_listening_sequences (
    album_id,
    album_name,
    artist_name,
    album_art_url,
    total_tracks,
    tracks_played,
    total_ms_played,
    first_played_at,
    last_played_at,
    is_full_album_listen
)

WITH complete_albums AS (

    SELECT
        tm.album_id,
        CONCAT(
            'spotify:track:',
            tm.spotify_id
        ) AS spotify_uri,
        am.album_art_url,
        am.total_tracks

    FROM track_metadata tm

    JOIN album_metadata am
        ON am.album_id = tm.album_id

    WHERE
        am.album_type = 'album'
        AND am.total_tracks > 1

    GROUP BY
        tm.album_id,
        am.album_name,
        am.album_art_url,
        am.total_tracks

    HAVING
        COUNT(*) = am.total_tracks
        AND COUNT(DISTINCT tm.spotify_id) = am.total_tracks
        AND COUNT(
            DISTINCT CONCAT(
                tm.disc_number,
                '-',
                tm.track_number
            )
        ) = am.total_tracks
    ),


-- ============================================================
-- Assign canonical track positions within each album
-- ============================================================

canonical_tracks AS (

    SELECT
        tm.album_id,
        tm.spotify_id,

        ROW_NUMBER() OVER (
            PARTITION BY tm.album_id
            ORDER BY
                tm.disc_number,
                tm.track_number
        ) AS album_track_position

    FROM track_metadata tm

    JOIN complete_albums ca
        ON ca.album_id = tm.album_id
),


-- ============================================================
-- Match listening events to canonical album tracks
-- ============================================================

ordered_events AS (

    SELECT
        w.play_number,
        w.played_at,
        w.spotify_uri,
        w.track_name,
        w.artist_name,
        w.ms_played,

        ct.album_id,
        ct.album_track_position,

        ca.album_name,
        ca.album_art_url,
        ca.total_tracks,

        LAG(ct.album_id) OVER (
            ORDER BY w.play_number
        ) AS previous_album_id,

        LAG(ct.album_track_position) OVER (
            ORDER BY w.play_number
        ) AS previous_album_track_position

    FROM listening_history_warehouse w

    LEFT JOIN canonical_tracks ct
        ON ct.spotify_uri = w.spotify_uri

    LEFT JOIN complete_albums ca
        ON ca.album_id = ct.album_id
),


-- ============================================================
-- Identify breaks between consecutive album tracks
-- ============================================================

sequence_breaks AS (

    SELECT
        *,

        CASE
            WHEN album_id IS NOT NULL
             AND previous_album_id = album_id
             AND previous_album_track_position =
                 album_track_position - 1
            THEN 0
            ELSE 1
        END AS sequence_break

    FROM ordered_events
),


-- ============================================================
-- Assign a sequence group to each consecutive run
-- ============================================================

grouped_sequences AS (

    SELECT
        *,

        SUM(sequence_break) OVER (
            ORDER BY play_number
            ROWS UNBOUNDED PRECEDING
        ) AS sequence_group

    FROM sequence_breaks
),


-- ============================================================
-- Summarize each consecutive album sequence
-- ============================================================

sequence_summary AS (

    SELECT
        sequence_group,

        album_id,

        MAX(album_name) AS album_name,
        MAX(artist_name) AS artist_name,
        MAX(album_art_url) AS album_art_url,
        MAX(total_tracks) AS total_tracks,

        COUNT(*) AS tracks_played,

        SUM(ms_played) AS total_ms_played,

        MIN(played_at) AS first_played_at,
        MAX(played_at) AS last_played_at,

        MIN(album_track_position) AS first_track_position,
        MAX(album_track_position) AS last_track_position,

        COUNT(DISTINCT spotify_uri) AS distinct_tracks

    FROM grouped_sequences

    WHERE album_id IS NOT NULL

    GROUP BY
        sequence_group,
        album_id
)


-- ============================================================
-- Insert qualifying complete album listens
-- ============================================================

SELECT

    album_id,
    album_name,
    artist_name,
    album_art_url,

    total_tracks,
    tracks_played,

    total_ms_played,

    first_played_at,
    last_played_at,

    1 AS is_full_album_listen

FROM sequence_summary

WHERE first_track_position = 1
  AND last_track_position = total_tracks
  AND tracks_played = total_tracks
  AND distinct_tracks = total_tracks;