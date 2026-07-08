/*
===============================================================
Listening Sessions
===============================================================

Author:
    Gabby Coleman

Purpose
-------
Groups individual plays into listening sessions.

A new session begins whenever there is a gap of
30 minutes or more between consecutive plays.
*/

USE spotify_analysis;

DROP TABLE IF EXISTS listening_sessions;

CREATE TABLE listening_sessions AS

WITH ordered AS (

    SELECT

        *,

        LAG(played_at)
        OVER (
            ORDER BY played_at
        ) AS previous_play

    FROM dashboard_data

),

session_flags AS (

    SELECT

        *,

        CASE

            WHEN previous_play IS NULL THEN 1

            WHEN TIMESTAMPDIFF(
                MINUTE,
                previous_play,
                played_at
            ) >= 30

            THEN 1

            ELSE 0

        END AS new_session

    FROM ordered

),

numbered AS (

    SELECT

        *,

        SUM(new_session)
        OVER (
            ORDER BY played_at
        ) AS session_id

    FROM session_flags

)

SELECT

    session_id,

    MIN(played_at) AS session_start,

    MAX(played_at) AS session_end,

    TIMESTAMPDIFF(

        MINUTE,

        MIN(played_at),

        MAX(played_at)

    ) AS session_length_minutes,

    COUNT(*) AS streams,

    COUNT(DISTINCT artist_name) AS artists,

    COUNT(DISTINCT album_name) AS albums,

    ROUND(

        SUM(ms_played) / 60000,

        2

    ) AS music_minutes

FROM numbered

GROUP BY

    session_id

ORDER BY

    session_start;
