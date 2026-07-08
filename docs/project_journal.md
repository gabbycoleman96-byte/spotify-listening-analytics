# project_journal.md

## Milestone 1

Imported Spotify Extended Streaming History into MySQL.

## Milestone 2

Created reusable Python ETL modules.

## Milestone 3

Implemented incremental liked-song extraction.

## Milestone 4

Automated recent-play downloads every 30 minutes using Windows Task
Scheduler.

## Milestone 5

Introduced recent_tracks_snapshot and listening_history_api architecture
to prevent API data loss.

## Milestone 6

Refactored analytics SQL into deterministic CREATE TABLE AS SELECT
scripts.

## Milestone 7

Automated analytics rebuilds and CSV exports.

## Milestone 8

Started the warehouse refactor.

-   Created the `dashboard_data` schema.
-   Built `dashboard_transform.py`.
-   Updated the ETL to prepare for direct loading into `dashboard_data`.
-   Began retiring `clean_data` and `listening_history_api`.

## Milestone 9

Retired the legacy analytics layer.

The project now centers on dashboard_data as the future warehouse and
Tableau fact table.

## Current Status

The ETL pipeline now performs end-to-end ingestion, loading, analytics
rebuilding, exporting, and logging with a single execution.

Current work is focused on designing an interactive Tableau dashboard
and planning a future dashboard_data fact table.
