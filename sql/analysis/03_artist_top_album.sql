/*==============================================================
03_artist_top_album.sql

Updates:
    - top_album
    - top_album_play_count
    - top_album_minutes
==============================================================*/

WITH album_stats AS (

    SELECT
        artist_name,
        album_name,

        COUNT(*) AS play_count,
        ROUND(SUM(ms_played) / 60000, 1) AS total_minutes

    FROM listening_history_warehouse

    WHERE artist_name IS NOT NULL
      AND album_name IS NOT NULL

    GROUP BY
        artist_name,
        album_name

),

ranked AS (

    SELECT
        artist_name,
        album_name,
        play_count,
        total_minutes,

        ROW_NUMBER() OVER (
            PARTITION BY artist_name
            ORDER BY
                play_count DESC,
                total_minutes DESC,
                album_name
        ) AS rn

    FROM album_stats

)

UPDATE artist_summary a

JOIN ranked r
    ON a.artist_name = r.artist_name

SET
    a.top_album = r.album_name,
    a.top_album_play_count = r.play_count,
    a.top_album_minutes = r.total_minutes

WHERE r.rn = 1;