# Changelog

All notable changes to Spotify Listening Analytics are documented here.

The project uses release milestones to distinguish stable functionality from future improvements.


# [2026-10-20] – External Music Metadata Enrichment

## Added

### MusicBrainz Track Enrichment

- Added `load/enrich_musicbrainz_tracks.py` to enrich Spotify tracks with MusicBrainz metadata.
- Added ISRC normalization to improve matching for identifiers containing formatting differences.
- Added matching logic that considers artist credits, track duration, and duplicate candidates.
- Cached lookup results and match statuses in `musicbrainz_track_metadata`.
- Added release-date enrichment to support canonical track selection and album-listening analysis.

### Last.fm Enrichment

- Added `load/enrich_lastfm.py` to retrieve track and artist metadata from Last.fm.
- Added track and artist metadata caching in `lastfm_track_metadata` and `lastfm_artist_metadata`.
- Added tag storage in `external_track_tags` and `external_artist_tags`.
- Added lookup statuses and error details to help distinguish successful matches from unsuccessful lookups.
- Added command-line options for testing limited batches and processing all eligible records.

## Changed

### Main ETL Pipeline

- Integrated MusicBrainz track enrichment and Last.fm track and artist enrichment into `main.py`.
- Added external enrichment warning handling so enrichment failures can be reported without automatically stopping the core pipeline.
- Kept external metadata in separate tables to avoid disrupting listening-history transformations and existing analytics.

### Project Documentation

- Updated `README.md` to document the current architecture, setup, enrichment workflows, and project status.
- Updated `docs/architecture.md` to describe pipeline execution, enrichment, and failure handling.
- Updated `docs/data_dictionary.md` to document external metadata tables and their current limitations.
- Updated `docs/design_decisions.md` to record enrichment architecture and related design choices.
- Updated `docs/project_journal.md` to record implementation history, validation results, and project milestones.

## Validated

- Completed initial MusicBrainz track-enrichment processing and retried records affected by ISRC formatting differences.
- Tested Last.fm track and artist enrichment with limited batches before integrating the jobs into the main pipeline.
- Confirmed that the external metadata tables retain lookup results for reuse by subsequent runs.

## Deferred

- MusicBrainz artist enrichment workflow.
- Last.fm similar-track retrieval and population of `lastfm_similar_tracks`.
- Using external tags to populate the warehouse's primary and secondary genre fields.
- Further use of enriched metadata in Tableau dashboards and playlist-generation workflows.


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
