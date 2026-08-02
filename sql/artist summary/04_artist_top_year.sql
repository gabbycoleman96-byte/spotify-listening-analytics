/*==============================================================
04_artist_top_year.sql

Updates:
    - top_year
    - top_year_play_count
    - top_year_minutes
==============================================================*/

WITH year_stats AS (

    SELECT
        artist_name,
        YEAR(Date) AS play_year,

        COUNT(*) AS play_count,
        ROUND(SUM(ms_played) / 60000, 1) AS total_minutes

    FROM spotify_listening_warehouse

    WHERE artist_name IS NOT NULL

    GROUP BY
        artist_name,
        YEAR(Date)

),

ranked AS (

    SELECT
        artist_name,
        play_year,
        play_count,
        total_minutes,

        ROW_NUMBER() OVER (
            PARTITION BY artist_name
            ORDER BY
                play_count DESC,
                total_minutes DESC,
                play_year DESC
        ) AS rn

    FROM year_stats

)

UPDATE artist_summary a

JOIN ranked r
    ON a.artist_name = r.artist_name

SET
    a.top_year = r.play_year,
    a.top_year_play_count = r.play_count,
    a.top_year_minutes = r.total_minutes

WHERE r.rn = 1;