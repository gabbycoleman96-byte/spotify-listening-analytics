/*
===============================================================
Track Summary
===============================================================

Rebuilds the track_summary table from clean_data.

Each row represents one unique Spotify track.

This table serves as the foundation for:

    • Top Songs
    • Most Played Tracks
    • Skip Analysis
    • Liked Song Analysis
    • Song Lifetime Statistics
*/

USE spotify_analysis;

DROP TABLE IF EXISTS track_summary;

CREATE TABLE track_summary AS

SELECT

    track_uri,

    track_name,

    artist_name,

    album_name,

    COUNT(*) AS total_streams,

    ROUND(SUM(Seconds) / 60, 2) AS total_minutes,

    MIN(Date) AS first_played,

    MAX(Date) AS last_played,

    COUNT(DISTINCT Year) AS active_years,

    COUNT(DISTINCT Date) AS listening_days,

    ROUND(AVG(Seconds) / 60, 2) AS avg_stream_minutes,

    SUM(
        CASE
            WHEN Skipped = 'True' THEN 1
            ELSE 0
        END
    ) AS skip_count,

    ROUND(
        SUM(
            CASE
                WHEN Skipped = 'True' THEN 1
                ELSE 0
            END
        ) / COUNT(*) * 100,
        2
    ) AS skip_rate,

    DATEDIFF(
        CURDATE(),
        MAX(Date)
    ) AS days_since_last_play

FROM clean_data

WHERE track_uri IS NOT NULL

GROUP BY

    track_uri,
    track_name,
    artist_name,
    album_name

ORDER BY

    total_streams DESC;
    
