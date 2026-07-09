/*
===============================================================
Recent Tracks Table
===============================================================
*/

USE spotify_analysis;

DROP TABLE IF EXISTS recent_tracks_snapshot;

CREATE TABLE recent_tracks_snapshot (

    played_at DATETIME NOT NULL,

    spotify_id VARCHAR(50) NOT NULL,

    spotify_uri VARCHAR(100) NOT NULL,

    track_name VARCHAR(255) NOT NULL,

    artist_name VARCHAR(255) NOT NULL,

    album_name VARCHAR(255),

    duration_ms INT NOT NULL,

    PRIMARY KEY (played_at, spotify_id)

);

