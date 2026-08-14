# Changelog

All notable changes to Spotify Listening Analytics are documented here.

The project uses release milestones to distinguish stable functionality from future improvements.

---

# [2026-08-13] – Dashboard Completion Checkpoint

## Current State

The core data engineering pipeline is operational and the project has moved into the **Dashboard Version 1.0.0 completion phase**.

The priority is now finishing the Tableau Public dashboard. Nonessential ETL refactoring is intentionally deferred.

---

## Added

### Raw Listening History

- Added the combined Spotify Extended Streaming History workflow.
- Current combined export contains approximately 824,845 records.
- Historical coverage currently extends from 2014-07-04 through 2026-08-07.

### Data Quality

Added/established warehouse quality handling for:

- Exact duplicate records
- Duplicate timestamp + Spotify track records
- Impossible overlapping playback
- Repeating playback-loop anomaly flags

Current anomaly fields:

```text
is_anomaly
anomaly_type
```

### Offline Playback Handling

Added correction logic using Spotify's `offline_timestamp` when available.

The export contains both Unix-second and Unix-millisecond timestamp values, so the transformation determines the timestamp scale before conversion.

The corrected `played_at` value is then used to generate date and time dimensions.

---

## Changed

### Warehouse

The active warehouse is:

```text
listening_history_warehouse
```

The raw source table is:

```text
listening_history_raw
```

The raw table remains unchanged during cleaning.

### ETL Scheduling

The project no longer relies on the Recently Played endpoint as a required recurring listening-history source.

The previous 30-minute schedule is therefore no longer necessary for the current architecture. The recurring job can run at a lower frequency appropriate to the current workflow.

### Project Priority

The project has moved from infrastructure development to dashboard completion.

---

## Validated

The current raw history was validated at:

```text
824,845 rows
First play: 2014-07-04 03:56:48
Last play:  2026-08-07 23:59:41
```

The rebuilt warehouse was also validated against the raw source and contains approximately 804,193 retained records after transformation.

---

## Deferred

The following are intentionally deferred rather than considered V1 blockers:

- Incremental warehouse loading
- Warehouse rebuild optimization
- Additional large-scale schema changes
- New external music-data integrations
- Playlist generation
- Further enrichment unless required by the dashboard

---

# [1.0.0] - Initial Pipeline Release

Version 1.0.0 established the core automated data engineering platform.

## Added

- Spotify Web API integration
- Historical Spotify Streaming History importer
- MySQL warehouse
- Python ETL pipeline
- Data transformation layer
- Duplicate protection
- SQL analytics
- Tableau-ready CSV exports
- Windows Task Scheduler automation
- Project documentation

## Changed

- Migrated from multiple manually maintained summary tables to a warehouse-first architecture.
- Retired legacy summary datasets.
- Centralized reusable analytics logic.

---

# Future

Future enhancements are tracked in `roadmap.md`.

The next major milestone is **Dashboard Version 1.0.0 completion**, not another ETL rewrite.
