# data_dictionary.md

## Core Tables

### liked_songs

Stores metadata for all liked songs.

Key fields:

-   spotify_id
-   spotify_uri
-   track_name
-   artist_name
-   album_name
-   release_date
-   added_to_library
-   duration_ms
-   popularity

------------------------------------------------------------------------

### recent_tracks_snapshot

Temporary mirror of Spotify's latest 50 plays.

Refreshed every ETL run.

------------------------------------------------------------------------

### listening_history_api

Permanent archive of recent plays collected through the Spotify API.

Grows continuously via INSERT IGNORE.

------------------------------------------------------------------------

### yearly_summary

Yearly listening metrics.

------------------------------------------------------------------------

### hourly_summary

Listening behavior by hour.

------------------------------------------------------------------------

### artist_lifetime_summary

Lifetime artist metrics.

------------------------------------------------------------------------

### artist_yearly_summary

Artist metrics by year.

------------------------------------------------------------------------

### track_summary

Lifetime track metrics.

------------------------------------------------------------------------

### liked_song_analysis

Analytics specific to liked songs.

------------------------------------------------------------------------

### etl_log

Stores pipeline execution history including runtime, row counts, status,
and errors.

------------------------------------------------------------------------

## dashboard_data (In Development)

Primary warehouse fact table.

Purpose: - Store one row per listening event. - Become the single source
of truth. - Feed analytics tables and Tableau.

Status: Schema created. ETL integration in progress.
