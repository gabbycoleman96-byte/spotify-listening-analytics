/*
===============================================================
Spotify Listening Warehouse
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Creates the primary fact table for the Spotify data warehouse.

Each row represents a single listening event.

This table serves as the central data source for:

• Tableau dashboards
• Analytics tables
• Future machine learning projects
• Portfolio demonstrations

Data Sources
------------
• Spotify Extended Streaming History
• Spotify Web API
*/

USE spotify_analysis;

DROP TABLE IF EXISTS listening_history_warehouse;

CREATE TABLE listening_history_warehouse (

    /* =======================================================
       Listening Event
       ======================================================= */

    played_at              DATETIME      NOT NULL,
    date                   DATE          NOT NULL,

    year                   SMALLINT      NOT NULL,
    quarter                TINYINT       NOT NULL,

    month_number           TINYINT       NOT NULL,
    month_name             VARCHAR(15)   NOT NULL,

    week                   TINYINT       NOT NULL,

    day                    TINYINT       NOT NULL,

    weekday_number         TINYINT       NOT NULL,
    weekday_name           VARCHAR(15)   NOT NULL,

    hour                   TINYINT       NOT NULL,
    hour_label             VARCHAR(5)    NOT NULL,

    time                   TIME          NOT NULL,

    /* =======================================================
       Playback
       ======================================================= */

    ms_played              INT           NOT NULL,
    duration_ms            INT,

    shuffle_state          BOOLEAN,
    skipped                BOOLEAN,

    /* =======================================================
       Track Information
       ======================================================= */

    track_name             VARCHAR(255)  NOT NULL,
    artist_name            VARCHAR(255)  NOT NULL,
    album_name             VARCHAR(255),

    spotify_id             VARCHAR(50)   NOT NULL,
    spotify_uri            VARCHAR(100),

    /* =======================================================
       Library Information
       ======================================================= */

    is_liked               BOOLEAN DEFAULT FALSE,

    /* =======================================================
       Genre Information
       ======================================================= */

    primary_genre          VARCHAR(100),
    secondary_genre        VARCHAR(100),

    /* =======================================================
       Album Artwork
       ======================================================= */

    album_art_url          VARCHAR(500),
    dominant_color         CHAR(7),

    /* =======================================================
       ETL Metadata
       ======================================================= */

    source                 ENUM(
                                'Spotify Export',
                                'Spotify API'
                           ) NOT NULL,

    imported_at            DATETIME NOT NULL
                           DEFAULT CURRENT_TIMESTAMP,

    /* =======================================================
       Keys
       ======================================================= */

    PRIMARY KEY (
        played_at,
        spotify_id
    )

);


ALTER TABLE listening_history_warehouse
ADD COLUMN session_id INT NULL,
ADD COLUMN session_start DATETIME NULL,
ADD COLUMN session_end DATETIME NULL,
ADD COLUMN session_duration_minutes DECIMAL(8,2) NULL,
ADD COLUMN session_stream_count SMALLINT NULL,
ADD COLUMN minutes_since_previous_play INT NULL,

ADD COLUMN play_number INT NULL,

ADD COLUMN play_of_day SMALLINT NULL,
ADD COLUMN play_of_week SMALLINT NULL,
ADD COLUMN play_of_month SMALLINT NULL,
ADD COLUMN play_of_year SMALLINT NULL,

ADD COLUMN previous_track VARCHAR(255) NULL,
ADD COLUMN previous_artist VARCHAR(255) NULL,
ADD COLUMN previous_album VARCHAR(255) NULL,

ADD COLUMN next_track VARCHAR(255) NULL,
ADD COLUMN next_artist VARCHAR(255) NULL,
ADD COLUMN next_album VARCHAR(255) NULL,

ADD COLUMN same_artist_as_previous BOOLEAN NULL,
ADD COLUMN same_album_as_previous BOOLEAN NULL,
ADD COLUMN same_song_as_previous BOOLEAN NULL,

ADD COLUMN artist_streak_id INT NULL,
ADD COLUMN artist_streak_length SMALLINT NULL,

ADD COLUMN album_streak_id INT NULL,
ADD COLUMN album_streak_length SMALLINT NULL,

ADD COLUMN song_streak_id INT NULL,
ADD COLUMN song_streak_length SMALLINT NULL,

ADD COLUMN skip_streak_id INT NULL,
ADD COLUMN skip_streak_length SMALLINT NULL,

ALTER TABLE listening_history_warehouse
MODIFY play_of_year INT UNSIGNED,
MODIFY play_number INT UNSIGNED,
MODIFY session_id INT UNSIGNED,
MODIFY artist_streak_id INT UNSIGNED,
MODIFY album_streak_id INT UNSIGNED,
MODIFY song_streak_id INT UNSIGNED,
MODIFY skip_streak_id INT UNSIGNED,
MODIFY minutes_since_previous_play INT;


ALTER TABLE listening_history_warehouse

ADD COLUMN play_in_session SMALLINT NULL,

ADD COLUMN is_first_play BOOLEAN NULL,
ADD COLUMN is_last_play BOOLEAN NULL,

ADD COLUMN artist_play_count INT UNSIGNED NULL,
ADD COLUMN album_play_count INT UNSIGNED NULL,
ADD COLUMN album_art_play_count INT NULL,
ADD COLUMN track_play_count INT UNSIGNED NULL,
ADD COLUMN album_longest_streak_days INT NULL;

