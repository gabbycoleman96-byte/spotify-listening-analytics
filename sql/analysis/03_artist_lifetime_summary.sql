/*
===============================================================
Artist Lifetime Summary
===============================================================

Master artist table used throughout the Tableau dashboard.
*/

USE spotify_analysis;

DROP TABLE IF EXISTS artist_lifetime_summary;

CREATE TABLE artist_lifetime_summary AS

SELECT

    artist_name,

    /* Overall Listening */

    COUNT(*) AS total_streams,

    ROUND(SUM(Seconds) / 60, 2) AS total_minutes,

    ROUND(SUM(Seconds) / 86400, 2) AS total_days,

    /* Timeline */

    MIN(Date) AS first_listen,

    MAX(Date) AS last_listen,

    COUNT(DISTINCT Year) AS active_years,

    /* Recency */

    DATEDIFF(CURDATE(), MAX(Date)) AS days_since_last_listen,

    /* Consistency */

    ROUND(
        COUNT(*) / COUNT(DISTINCT Year),
        2
    ) AS avg_streams_per_year

FROM clean_data

WHERE artist_name IS NOT NULL

GROUP BY artist_name

ORDER BY total_streams DESC;