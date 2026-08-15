/*==============================================================
02_artist_top_song.sql

Updates:
    - top_song
    - top_song_play_count
    - top_song_minutes
==============================================================*/

WITH song_stats AS (

    SELECT
        artist_name,
        track_name,

        COUNT(*) AS play_count,
        ROUND(SUM(ms_played) / 60000, 1) AS total_minutes

    FROM listening_history_warehouse

    WHERE artist_name IS NOT NULL
      AND track_name IS NOT NULL

    GROUP BY
        artist_name,
        track_name

),

ranked AS (

    SELECT
        artist_name,
        track_name,
        play_count,
        total_minutes,

        ROW_NUMBER() OVER (
            PARTITION BY artist_name
            ORDER BY
                play_count DESC,
                total_minutes DESC,
                track_name
        ) AS rn

    FROM song_stats

)

UPDATE artist_summary a

JOIN ranked r
    ON a.artist_name = r.artist_name

SET
    a.top_song = r.track_name,
    a.top_song_play_count = r.play_count,
    a.top_song_minutes = r.total_minutes

WHERE r.rn = 1;