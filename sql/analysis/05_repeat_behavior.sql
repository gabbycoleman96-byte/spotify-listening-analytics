/*
===============================================================
Repeat Behavior
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Analyzes repeat listening behavior for every track.

Supports:

• Most Replayed Songs
• One-Hit Wonders
• Songs on Repeat
• Repeat Behavior Dashboard
*/

USE spotify_analysis;

DROP TABLE IF EXISTS repeat_behavior;

CREATE TABLE repeat_behavior AS

SELECT

    spotify_id,

    spotify_uri,

    track_name,

    artist_name,

    album_name,

    COUNT(*) AS total_streams,

    ROUND(
        SUM(ms_played) / 60000,
        2
    ) AS total_minutes,

    MIN(played_at) AS first_listened,

    MAX(played_at) AS last_listened,

    DATEDIFF(
        MAX(played_at),
        MIN(played_at)
    ) AS listening_span_days,

    COUNT(DISTINCT date) AS active_days,

    ROUND(
        COUNT(*) /
        NULLIF(COUNT(DISTINCT date),0),
        2
    ) AS avg_streams_per_active_day,

    ROUND(
        COUNT(*) /
        NULLIF(
            DATEDIFF(
                MAX(played_at),
                MIN(played_at)
            ),
            0
        ),
        4
    ) AS avg_streams_per_day

FROM dashboard_data

GROUP BY

    spotify_id,
    spotify_uri,
    track_name,
    artist_name,
    album_name

ORDER BY

    total_streams DESC;
