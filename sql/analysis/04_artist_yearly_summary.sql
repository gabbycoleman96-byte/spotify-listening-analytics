/*
===============================================================
Artist Yearly Summary
===============================================================

Rebuilds the artist_yearly_summary table from clean_data.

Each row represents one artist in one calendar year.

This table serves as the foundation for:
    • Artist growth charts
    • Discovery timelines
    • Peak listening years
    • Year-over-year comparisons
    • Trend analysis
*/

USE spotify_analysis;

DROP TABLE IF EXISTS artist_yearly_summary;

CREATE TABLE artist_yearly_summary AS

SELECT

    artist_name,

    Year,

    COUNT(*) AS total_streams,

    ROUND(SUM(Seconds) / 60, 2) AS total_minutes,

    MIN(Date) AS first_stream,

    MAX(Date) AS last_stream,

    COUNT(DISTINCT track_uri) AS unique_tracks,

    COUNT(DISTINCT album_name) AS unique_albums,

    ROUND(AVG(Seconds) / 60, 2) AS avg_stream_length_minutes

FROM clean_data

WHERE artist_name IS NOT NULL

GROUP BY

    artist_name,
    Year

ORDER BY

    artist_name,
    Year;