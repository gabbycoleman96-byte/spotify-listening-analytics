/*
===============================================================
Dashboard Data
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

DROP TABLE IF EXISTS dashboard_data;

CREATE TABLE dashboard_data (

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