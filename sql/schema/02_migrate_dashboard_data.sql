/*
===============================================================
Migrate Dashboard Data
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Populates dashboard_data from the existing warehouse tables.

Data Sources
------------
1. clean_data
2. listening_history_api

Duplicate rows are automatically ignored by the composite
primary key (played_at, spotify_id).
*/

USE spotify_analysis;

-- ============================================================
-- Import Spotify Extended Streaming History
-- ============================================================

INSERT IGNORE INTO dashboard_data (

    played_at,
    date,
    year,
    quarter,
    month_number,
    month_name,
    week,
    day,
    weekday_number,
    weekday_name,
    hour,
    hour_label,
    time,

    ms_played,
    duration_ms,

    shuffle_state,
    skipped,

    track_name,
    artist_name,
    album_name,

    spotify_id,
    spotify_uri,

    is_liked,

    source

)

SELECT

    Time_stamp,

    DATE(Time_stamp),

    YEAR(Time_stamp),

    QUARTER(Time_stamp),

    MONTH(Time_stamp),

    MONTHNAME(Time_stamp),

    WEEK(Time_stamp, 3),

    DAY(Time_stamp),

    WEEKDAY(Time_stamp) + 1,

    DAYNAME(Time_stamp),

    HOUR(Time_stamp),

    CASE
        WHEN HOUR(Time_stamp) = 0 THEN '12 AM'
        WHEN HOUR(Time_stamp) < 12 THEN CONCAT(HOUR(Time_stamp), ' AM')
        WHEN HOUR(Time_stamp) = 12 THEN '12 PM'
        ELSE CONCAT(HOUR(Time_stamp) - 12, ' PM')
    END,

    TIME(Time_stamp),

    Seconds * 1000,

    NULL,

    Shuffle,

    Skipped,

    track_name,

    artist_name,

    album_name,

    track_uri,

    CONCAT('spotify:track:', track_uri),

    FALSE,

    'Spotify Export'

FROM clean_data;


-- ============================================================
-- Mark songs that are currently liked
-- ============================================================

UPDATE dashboard_data d

INNER JOIN liked_songs l

ON d.spotify_id = l.spotify_id

SET d.is_liked = TRUE;


-- ============================================================
-- Import API Listening History
-- ============================================================

INSERT IGNORE INTO dashboard_data (

    played_at,
    date,
    year,
    quarter,
    month_number,
    month_name,
    week,
    day,
    weekday_number,
    weekday_name,
    hour,
    hour_label,
    time,

    ms_played,
    duration_ms,

    shuffle_state,
    skipped,

    track_name,
    artist_name,
    album_name,

    spotify_id,
    spotify_uri,

    is_liked,

    source

)

SELECT

    played_at,

    DATE(played_at),

    YEAR(played_at),

    QUARTER(played_at),

    MONTH(played_at),

    MONTHNAME(played_at),

    WEEK(played_at, 3),

    DAY(played_at),

    WEEKDAY(played_at) + 1,

    DAYNAME(played_at),

    HOUR(played_at),

    CASE
        WHEN HOUR(played_at) = 0 THEN '12 AM'
        WHEN HOUR(played_at) < 12 THEN CONCAT(HOUR(played_at), ' AM')
        WHEN HOUR(played_at) = 12 THEN '12 PM'
        ELSE CONCAT(HOUR(played_at) - 12, ' PM')
    END,

    TIME(played_at),

    duration_ms,

    duration_ms,

    NULL,

    NULL,

    track_name,

    artist_name,

    album_name,

    spotify_id,

    spotify_uri,

    EXISTS (
        SELECT 1
        FROM liked_songs l
        WHERE l.spotify_id = listening_history_api.spotify_id
    ),

    'Spotify API'

FROM listening_history_api;