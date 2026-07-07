/*
===============================================================
Yearly Summary
===============================================================

Rebuilds the yearly_summary table from clean_data.
*/

USE spotify_analysis;

DROP TABLE IF EXISTS yearly_summary;

CREATE TABLE yearly_summary AS

SELECT

    YEAR,

    COUNT(*) AS streams,

    ROUND(SUM(seconds) / 60, 2) AS minutes_played,

    COUNT(DISTINCT track_uri) AS unique_tracks,

    COUNT(DISTINCT artist_name) AS unique_artists,

    COUNT(DISTINCT album_name) AS unique_albums

FROM clean_data

GROUP BY YEAR

ORDER BY YEAR;