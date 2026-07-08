/*
===============================================================
Forgotten Favorites
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Identifies artists that were once heavily listened to
but have not been played recently.

Supports:

• Rediscover Your Music
• Forgotten Favorites
• Artists You've Drifted Away From
*/

USE spotify_analysis;

DROP TABLE IF EXISTS forgotten_favorites;

CREATE TABLE forgotten_favorites AS

SELECT

    artist_name,

    COUNT(*) AS lifetime_streams,

    ROUND(
        SUM(ms_played) / 60000,
        2
    ) AS lifetime_minutes,

    MIN(played_at) AS first_listened,

    MAX(played_at) AS last_listened,

    DATEDIFF(
        CURDATE(),
        MAX(played_at)
    ) AS days_since_last_listened,

    COUNT(DISTINCT track_name) AS unique_tracks,

    COUNT(DISTINCT album_name) AS unique_albums,

    COUNT(DISTINCT date) AS active_days,

    ROUND(
        COUNT(*) /
        NULLIF(COUNT(DISTINCT date), 0),
        2
    ) AS avg_streams_per_active_day

FROM dashboard_data

GROUP BY
    artist_name

HAVING

    lifetime_streams >= 25

    AND

    days_since_last_listened >= 90

ORDER BY

    lifetime_minutes DESC,

    days_since_last_listened DESC;
