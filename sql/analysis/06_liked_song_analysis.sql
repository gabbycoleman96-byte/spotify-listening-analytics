/*
===============================================================
Liked Song Analysis
===============================================================

Combines Spotify library data with track listening statistics.
*/

USE spotify_analysis;

DROP TABLE IF EXISTS liked_song_analysis;

CREATE TABLE liked_song_analysis AS

SELECT

    t.track_uri,

    t.track_name,

    t.artist_name,

    t.album_name,

    CASE
        WHEN l.spotify_uri IS NULL THEN 'No'
        ELSE 'Yes'
    END AS is_liked,

    l.added_to_library,

    t.total_streams,

    t.total_minutes,

    t.first_played,

    t.last_played,

    t.active_years,

    t.listening_days,

    t.avg_stream_minutes,

    t.skip_count,

    t.skip_rate,

    t.days_since_last_play

FROM track_summary t

LEFT JOIN liked_songs l

    ON t.track_uri = l.spotify_uri

ORDER BY

    t.total_streams DESC;