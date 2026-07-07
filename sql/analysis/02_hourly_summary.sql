/*
===============================================================
Hourly Summary
===============================================================

Rebuilds the hourly_summary table from clean_data.

This table powers the listening clock visualization in Tableau.
*/

USE spotify_analysis;

DROP TABLE IF EXISTS hourly_summary;

CREATE TABLE hourly_summary AS

SELECT

    YEAR,

    MONTH,

    hour_of_day,

    CASE
        WHEN hour_of_day = 0 THEN '12 AM'
        WHEN hour_of_day < 12 THEN CONCAT(hour_of_day, ' AM')
        WHEN hour_of_day = 12 THEN '12 PM'
        ELSE CONCAT(hour_of_day - 12, ' PM')
    END AS hour_label,

    streams,

    minutes_played

FROM (

    SELECT

        YEAR,

        MONTH,

        HOUR(Time) AS hour_of_day,

        COUNT(*) AS streams,

        ROUND(SUM(Seconds) / 60, 2) AS minutes_played

    FROM clean_data

    GROUP BY

        YEAR,
        MONTH,
        HOUR(Time)

) AS hourly

ORDER BY

    YEAR,
    MONTH,
    hour_of_day;