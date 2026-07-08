# CHANGELOG

------------------------------------------------------------------------

## Unreleased

### Removed

Retired all first-generation summary tables.

### Changed

-   Introduced `dashboard_data` as the future warehouse fact table.
-   Added `dashboard_transform.py`.
-   Began migrating the ETL away from `clean_data` and
    `listening_history_api`.
-  Tableau will use dashboard_data as its primary data source.

------------------------------------------------------------------------

## v0.9.0 --- Automated Analytics Pipeline

### Added

-   Automatic analytics table rebuilds.
-   Automatic CSV exports for Tableau.
-   Central pipeline configuration (`config/pipeline.py`).
-   SQL file execution from Python.
-   Reusable export module.

### Changed

-   ETL now rebuilds analytics and exports datasets during every run.

------------------------------------------------------------------------

## v0.8.0 --- Listening History Archive

### Added

-   `recent_tracks_snapshot` table.
-   `listening_history_api` permanent archive.
-   Snapshot → archive workflow using `INSERT IGNORE`.

### Changed

-   Recent plays are no longer stored directly in a single table.
-   Listening history gaps are prevented while waiting for future
    Spotify exports.

------------------------------------------------------------------------

## v0.7.0 --- Analytics SQL Refactor

### Added

-   Modern SQL analytics scripts using:
    -   `DROP TABLE IF EXISTS`
    -   `CREATE TABLE ... AS SELECT`

### Refactored

-   `yearly_summary`
-   `hourly_summary`
-   `artist_lifetime_summary`
-   `artist_yearly_summary`
-   `track_summary`
-   `liked_song_analysis`

------------------------------------------------------------------------

## v0.6.0 --- Incremental API Extraction

### Added

-   Incremental liked-song downloads.
-   Duplicate-safe loading using `INSERT IGNORE`.

### Changed

-   Liked songs are no longer downloaded in full on every ETL run.

------------------------------------------------------------------------

## v0.5.0 --- Automated ETL

### Added

-   Windows Task Scheduler automation.
-   ETL logging.
-   Runtime summaries.
-   Modular loading functions.

------------------------------------------------------------------------

## v0.4.0 --- Python ETL

### Added

-   Spotify API integration.
-   Modular extraction modules.
-   MySQL loading modules.
-   Reusable helper utilities.

------------------------------------------------------------------------

## v0.3.0 --- Analytics Warehouse

### Added

-   Initial analytics tables.
-   SQL transformations.
-   Artist and track summaries.

------------------------------------------------------------------------

## v0.2.0 --- Initial Database

### Added

-   MySQL database.
-   Import of Spotify Extended Streaming History.
-   Initial data cleaning workflow.

------------------------------------------------------------------------

## v0.1.0 --- Project Started

### Added

-   Repository created.
-   Initial project architecture.
-   Documentation.
-   Planning and design.
