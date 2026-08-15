DROP TABLE IF EXISTS artist_summary;

CREATE TABLE artist_summary AS

WITH artist_stats AS (

    SELECT
        artist_name,

        COUNT(*) AS total_streams,

        SUM(ms_played) AS total_milliseconds,

        ROUND(SUM(ms_played) / 60000, 1) AS total_minutes,

        ROUND(SUM(ms_played) / 3600000, 1) AS total_hours,

        ROUND(SUM(ms_played) / 86400000, 1) AS total_days,

        MIN(Date) AS first_played,

        MAX(Date) AS last_played,

        SUM(is_liked) AS liked_song_count

    FROM listening_history_warehouse

    WHERE artist_name IS NOT NULL

    GROUP BY artist_name

),

ranked AS (

    SELECT
        *,
        DENSE_RANK() OVER (
            ORDER BY total_streams DESC
        ) AS artist_rank

    FROM artist_stats

)

SELECT
    artist_name,

    total_streams,
    total_milliseconds,
    total_minutes,
    total_hours,
    total_days,

    first_played,
    last_played,
    liked_song_count,

    artist_rank,

    CAST(NULL AS CHAR(255)) AS top_song,
    CAST(NULL AS UNSIGNED) AS top_song_play_count,
    CAST(NULL AS DECIMAL(10,1)) AS top_song_minutes,

    CAST(NULL AS CHAR(255)) AS top_album,
    CAST(NULL AS UNSIGNED) AS top_album_play_count,
    CAST(NULL AS DECIMAL(10,1)) AS top_album_minutes,

    CAST(NULL AS UNSIGNED) AS top_year,
    CAST(NULL AS UNSIGNED) AS top_year_play_count,
    CAST(NULL AS DECIMAL(10,1)) AS top_year_minutes,

    CAST(NULL AS CHAR(1000)) AS artist_note

FROM ranked

ORDER BY artist_rank;