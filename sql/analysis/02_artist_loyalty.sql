/*
===============================================================
Artist Loyalty
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Measures long-term listening behavior for every artist.

This table supports:

• Most Loyal Artists
• Artist Longevity
• Listening Consistency
• Favorite Artists
• Returning Artists
*/

USE spotify_analysis;

DROP TABLE IF EXISTS artist_loyalty;

CREATE TABLE artist_loyalty AS

SELECT

    artist_name,

    MIN(played_at) AS first_listened,

    MAX(played_at) AS most_recent_listened,

    DATEDIFF(
        MAX(played_at),
        MIN(played_at)
    ) AS listening_span_days,

    COUNT(*) AS total_streams,

    COUNT(DISTINCT track_name) AS unique_tracks,

    COUNT(DISTINCT album_name) AS unique_albums,

    COUNT(DISTINCT date) AS active_days,

    COUNT(DISTINCT year) AS active_years,

    ROUND(
        SUM(ms_played) / 60000,
        2
    ) AS total_minutes,

    ROUND(
        COUNT(*) /
        NULLIF(COUNT(DISTINCT year), 0),
        2
    ) AS avg_streams_per_year,

    ROUND(
        SUM(ms_played) /
        NULLIF(COUNT(DISTINCT date), 0) /
        60000,
        2
    ) AS avg_minutes_per_active_day,

    ROUND(
        COUNT(*) /
        NULLIF(DATEDIFF(
            MAX(played_at),
            MIN(played_at)
        ), 0),
        2
    ) AS avg_streams_per_day

FROM dashboard_data

GROUP BY
    artist_name

ORDER BY
    total_minutes DESC;
