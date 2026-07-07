/*
===============================================================
Liked Songs Table
===============================================================
*/

USE spotify_analysis;

DROP TABLE IF EXISTS liked_songs;

CREATE TABLE liked_songs (

    spotify_id VARCHAR(50) PRIMARY KEY,

    spotify_uri VARCHAR(100) NOT NULL,

    track_name VARCHAR(255) NOT NULL,

    artist_name VARCHAR(255) NOT NULL,

    album_name VARCHAR(255),

    release_date DATE,

    added_to_library DATETIME NOT NULL,

    duration_ms INT NOT NULL,

    popularity INT

);