# design_decisions.md

## Guiding Principles

-   Modular architecture
-   Reusable functions
-   SQL-first analytics
-   Production-style ETL
-   Clear naming conventions
-   Extensive documentation
-   Tableau-ready outputs

## Major Decisions

### Incremental liked songs

Only new liked songs are downloaded by checking the newest
added_to_library value stored in MySQL.

### Snapshot + Archive

recent_tracks_snapshot mirrors Spotify's latest 50 plays.

listening_history_api is the permanent archive protecting against data
loss between Spotify exports.

### Analytics Tables

Analytics tables are rebuilt from SQL scripts using:

-   DROP TABLE IF EXISTS
-   CREATE TABLE AS SELECT

instead of multi-step UPDATE workflows.

### Pipeline Configuration

Execution order is centralized in config/pipeline.py.

### Tableau Strategy

Analytics tables are exported automatically as CSV files.

Future work will consolidate these into a single Tableau-friendly fact
table after the next Spotify Extended Streaming History export.


## Dashboard Data Warehouse

A new warehouse table named `dashboard_data` has been introduced.

Design goals:

-   One row per listening event.
-   Single source of truth.
-   Feed analytics tables.
-   Feed Tableau.
-   Support future enrichment.

Transformation logic is now centralized in Python
(`dashboard_transform.py`) so both API and export imports will share the
same business rules.


## Summary Table Retirement

Removed: - yearly_summary - hourly_summary - artist_lifetime_summary -
artist_yearly_summary - track_summary - liked_song_analysis

Decision: A single fact table supports global filtering, reduces ETL
complexity, and better matches modern BI architecture.
