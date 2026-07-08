/*
===============================================================
Artist Discovery
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Creates a table containing the first time each artist
was discovered.

This table supports:

• Discovery Timeline
• New Artists by Year
• New Artists by Month
• Artist Discovery Statistics
*/

USE spotify_analysis;

DROP TABLE IF EXISTS artist_discovery;

CREATE TABLE artist_discovery AS

SELECT

    artist_name,

    MIN(played_at) AS first_listened,

    DATE(MIN(played_at)) AS first_listened_date,

    YEAR(MIN(played_at)) AS discovery_year,

    QUARTER(MIN(played_at)) AS discovery_quarter,

    MONTH(MIN(played_at)) AS discovery_month_number,

    MONTHNAME(MIN(played_at)) AS discovery_month_name,

    WEEK(MIN(played_at), 3) AS discovery_week,

    DAY(MIN(played_at)) AS discovery_day,

    DAYNAME(MIN(played_at)) AS discovery_weekday,

    HOUR(MIN(played_at)) AS discovery_hour,

    CASE
        WHEN HOUR(MIN(played_at)) = 0 THEN '12 AM'
        WHEN HOUR(MIN(played_at)) < 12 THEN CONCAT(HOUR(MIN(played_at)), ' AM')
        WHEN HOUR(MIN(played_at)) = 12 THEN '12 PM'
        ELSE CONCAT(HOUR(MIN(played_at)) - 12, ' PM')
    END AS discovery_hour_label,

    COUNT(*) AS lifetime_streams,

    COUNT(DISTINCT track_name) AS unique_tracks,

    SUM(ms_played) AS lifetime_ms_played,

    ROUND(SUM(ms_played) / 60000, 2) AS lifetime_minutes

FROM dashboard_data

GROUP BY
    artist_name

ORDER BY
    first_listened;
