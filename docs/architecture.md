# System Architecture

## 1. Purpose

Spotify Listening Analytics is a locally executed data engineering pipeline that transforms Spotify listening history into a MySQL analytical warehouse, enriches music entities with metadata, generates reusable SQL analytics, and exports datasets for Tableau Public.

The architecture separates five main responsibilities:

1. Source data ingestion and preservation
2. Spotify metadata and identity management
3. External music metadata enrichment
4. Warehouse transformation and analytical processing
5. Tableau dataset generation and pipeline monitoring

Python orchestrates the workflow, MySQL stores the data, SQL provides reusable analytical logic, and Tableau Public presents the results.

The implementation described here reflects the current repository structure. Future features are documented separately in `roadmap.md`.

---

## 2. System Overview

```text
                    SOURCE DATA
                         |
             +-----------+-----------+
             |                       |
             v                       v
    Spotify Extended           Spotify Web API
    Streaming History          Library / Metadata
             |                       |
             v                       v
    listening_history_raw       liked_songs
             |                       |
             +-----------+-----------+
                         |
                         v
                 MAIN ETL PIPELINE
                     main.py
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
    Warehouse Build   Song Identity   Spotify Metadata
                      Mapping         Tracks / Artists
          |              |              |
          +--------------+--------------+
                         |
                         v
              EXTERNAL ENRICHMENT
                         |
             +-----------+-----------+
             |                       |
             v                       v
         MusicBrainz                Last.fm
      Recording / Release      Tracks / Artists
             |                       |
             +-----------+-----------+
                         |
                         v
                EXTERNAL CACHE TABLES
                         |
                         v
                WAREHOUSE ENRICHMENT
                         |
                         v
            listening_history_warehouse
                         |
             +-----------+-----------+
             |                       |
             v                       v
       SQL Analytics           Tableau CSV Exports
                                     |
                                     v
                               Tableau Public

             ETL Execution Logging
                    etl_log
```

The diagram represents the major responsibilities and data relationships. It is not intended to imply that every component reads and writes directly to every other component.

---

## 3. Application Entry Point and Orchestration

### `main.py`

`main.py` coordinates the primary ETL workflow. Individual stages are implemented in separate modules so extraction, loading, transformation, enrichment, analytics, and export logic remain reusable.

The current execution order is:

| Order | Stage | Responsibility |
|---:|---|---|
| 1 | Liked Songs | Download new liked songs and insert them into MySQL |
| 2 | Listening History Warehouse | Build the warehouse from raw listening history |
| 3 | Song Identity Map | Rebuild the permanent song identity mapping |
| 4 | Canonical URI Mapping | Apply canonical Spotify song identities |
| 5 | Artist Metadata | Retrieve metadata for artists requiring it |
| 6 | Track Metadata | Retrieve missing Spotify track metadata |
| 7 | External Music Metadata | Run MusicBrainz and Last.fm enrichment |
| 8 | Album Art | Update hosted album artwork references |
| 9 | Warehouse Enrichment | Rebuild the warehouse with enrichment data |
| 10 | Analytics | Rebuild SQL analytics tables |
| 11 | Tableau Export | Export configured datasets to CSV |
| 12 | ETL Logging | Record execution results |

The optional Recently Played stage remains implemented in `main.py`, but its call is currently commented out. It is not part of the normal execution sequence.

The numbered console stage headers retain a slot for that optional stage, so displayed stage numbers may not match the count of stages actually executed.

### Stage results

Pipeline stages return a `StageResult` object containing applicable counts and runtime information. The external enrichment stage also carries an optional error message.

The pipeline prints a performance summary after the stages finish and writes a run record to `etl_log`.

---

## 4. Source and Ingestion Layer

### Spotify Extended Streaming History

The historical Spotify export is the principal source of playback events.

Export files are combined and loaded into the MySQL table:

`listening_history_raw`

The raw table is preserved as the source for warehouse rebuilding. Cleaning and transformation operate downstream rather than modifying the raw records.

The source import and replacement procedure is documented in:

`utils/new_spotify_export/spotify_export_update_instructions.md`

### Liked Songs

The liked-songs extraction stage checks the latest date represented in the existing `liked_songs` table and uses that information when requesting new liked-song data.

New records are loaded with duplicate protection.

### Recently Played

A Recently Played extraction workflow exists in `extract/recent_tracks.py` and is orchestrated through an optional stage in `main.py`.

That stage can refresh a recent-track snapshot and append API-derived play records to the raw listening-history table. Because the call is currently disabled, this is not a required input to the normal pipeline.

API-derived records have different source-field availability from the historical export. The extraction stage supplies null values for unavailable fields and identifies the records as coming from the Spotify API.

---

## 5. Spotify Metadata and Identity Layer

Spotify metadata is maintained separately from the raw listening events.

### Track metadata

`load/load_track_metadata.py`

This module identifies Spotify track IDs that lack metadata, retrieves the available metadata through the Spotify API, and loads it into the database.

The missing-track query draws from both the listening-history warehouse and liked songs.

### Artist metadata

`load/load_artist_metadata.py`

This module identifies artists associated with tracks that lack complete artist metadata, retrieves their information, and updates `artist_metadata`.

The current implementation limits a retrieval batch to 600 artist IDs.

### Album metadata and artwork

Album information is stored in the album metadata structures. Artwork processing is handled by:

`utils/album_art_manager.py`

The artwork manager downloads artwork, stores image files locally, and updates album metadata with hosted image URLs.

### Song identity mapping

`transform/build_song_identity_map.py`

The permanent `song_identity_map` is built from accepted identity decisions stored in:

`data/investigative/song_identity_review.csv`

The script uses those accepted decisions rather than rerunning the original identity investigation.

The resulting mapping groups Spotify track IDs that have been accepted as representations of the same underlying song.

### Canonical Spotify URIs

`transform/apply_canonical_song_uris.py`

This module rebuilds the compatibility mapping in `canonical_song_uris` from `song_identity_map` and updates canonical identities in the warehouse.

Updates are processed in batches, and the module includes a verification step for remaining mismatches.

Canonical song identity is distinct from recording identity: a canonical song group does not necessarily mean every version has identical audio, duration, or release metadata.

---

## 6. External Music Metadata Enrichment

External enrichment supplements Spotify's own catalog information with data from MusicBrainz and Last.fm.

The enrichment scripts run as separate Python modules. `main.py` launches them through subprocess calls using the active Python interpreter.

The external enrichment stage runs in this order:

1. MusicBrainz track metadata
2. Last.fm track metadata
3. Last.fm artist metadata

Each script owns its API requests, lookup queues, rate limiting, and database writes.

### 6.1 MusicBrainz

Module:

`load/enrich_musicbrainz_tracks.py`

MusicBrainz enrichment uses available ISRC identifiers to find candidate recordings. Matching logic evaluates recording title, artist credits, and duration where available.

The script records outcomes such as:

- `matched`
- `not_found`
- `ambiguous`
- `error`

It also stores match scores and available recording and release information.

The first release date is retained with its available precision. This allows a year-only or month-only date to remain distinguishable from a full calendar date.

Results are written to:

`musicbrainz_track_metadata`

The module is designed to operate independently from the core Spotify metadata tables.

### 6.2 Last.fm

Module:

`load/enrich_lastfm.py`

Last.fm enrichment supports two entity types:

- Tracks
- Artists

For tracks, the script retrieves available community statistics, descriptions, URLs, and tags.

For artists, it retrieves corresponding artist metadata, community statistics, descriptions, and tags.

The metadata cache tables are:

- `lastfm_track_metadata`
- `lastfm_artist_metadata`

Source-attributed tags are stored in:

- `external_track_tags`
- `external_artist_tags`

The script uses the `LASTFM_API_KEY` environment variable. Credentials remain in the local environment configuration and should not be committed to the repository.

Last.fm listeners and play counts describe activity reported by Last.fm's community. They are not personal Spotify play counts.

### 6.3 Cache and queue behavior

The enrichment modules query their existing metadata tables to identify eligible records. Successfully cached lookups are generally reused instead of fetched again.

The `--all` argument means processing all records considered eligible by a script's queue logic. It does not mean every record is blindly re-requested.

Each module can also be run separately with a limited batch for validation or troubleshooting.

Example commands:

```powershell
python -m load.enrich_musicbrainz_tracks --limit 10

python -m load.enrich_lastfm --entity tracks --limit 10

python -m load.enrich_lastfm --entity artists --limit 10
```

For full eligible queues, the scripts support `--all`.

The modules are deliberately rate-limited to reduce pressure on external services. Large initial backfills can take hours.

### 6.4 Failure handling

The external orchestration checks subprocess return codes and catches failures when launching the enrichment commands.

When a command fails, the pipeline records a warning and continues to later stages. The warning is propagated through the stage result so the overall ETL run can record a `Warning` status.

This protects the core workflow from a subprocess failure, but it does not guarantee that every individual API lookup succeeded. A script that catches a lookup error internally and exits with code zero may complete without causing the orchestrator to mark the stage as failed.

Individual lookup outcomes remain available in the enrichment tables.

---

## 7. Warehouse Transformation

The warehouse transformation layer builds a DataFrame from the raw listening history and adds the fields required for analysis.

Primary module:

`transform/warehouse_transform.py`

Supporting logic is divided between cleaning and enrichment modules.

### Transformation flow

1. Read `listening_history_raw` from MySQL.
2. Clean duplicate and invalid playback records according to the configured rules.
3. Rename Spotify source columns to warehouse-friendly names.
4. Extract Spotify identifiers.
5. Derive calendar and time dimensions.
6. Add metadata and listening-related fields.
7. Return the transformed warehouse DataFrame.

### Cleaning rules

The cleaning layer includes logic for:

- Removing exact duplicates
- Handling repeated timestamp and track combinations
- Excluding playback events that violate the project's impossible-overlap rules
- Normalizing source values where required

The exact behavior is defined in the transformation code, not by this document alone.

### Offline playback

When a valid offline timestamp is available for an offline play, the transformation can use it as the canonical playback timestamp.

The source export may contain offline timestamps represented at different Unix time scales. The transformation detects the scale before conversion.

Calendar dimensions are derived from the resulting canonical `played_at` value.

### Anomaly flags

Suspicious repeating playback patterns can be retained and flagged instead of being silently removed.

The warehouse uses fields including:

- `is_anomaly`
- `anomaly_type`

These fields allow downstream analyses to exclude or investigate flagged events as needed.

---

## 8. Warehouse Storage and Enrichment

### `listening_history_warehouse`

The warehouse is the main analytical table for listening-history reporting.

Its intended grain is one retained listening event per row after transformation and cleaning.

It combines playback details with relevant Spotify identifiers, metadata, time dimensions, and data-quality fields.

### Warehouse rebuild strategy

The primary warehouse stage rebuilds the warehouse from the available raw listening history and replaces the existing warehouse contents.

After Spotify and external metadata stages run, the warehouse enrichment stage rebuilds the enriched DataFrame and replaces the warehouse again.

This order allows the enrichment stage to use metadata fetched earlier in the same pipeline run.

The current implementation favors reproducibility and a straightforward rebuild process over incremental warehouse loading. Incremental processing remains a potential future improvement.

### External metadata separation

MusicBrainz and Last.fm results are cached in separate tables. Their data can support later analytical enrichment without changing the raw listening history.

The precise external fields included in the warehouse depend on the current warehouse enrichment implementation.

---

## 9. SQL Analytics Layer

Location:

`sql/analysis/`

Module:

`transform/rebuild_summary_tables.py`

The analytics stage executes the configured SQL scripts in sorted filename order, with an explicit exclusion for the retired `09_normalize_song_uris.sql` script.

These scripts build or refresh summary tables and other analytical structures used downstream.

Reusable business logic is generally placed in SQL or upstream transformation code rather than duplicated across Tableau worksheets.

The list of executed SQL scripts is determined by the files present in the analysis directory and the exclusions in the rebuild module.

---

## 10. Export and Presentation Layer

### Tableau exports

Configuration:

`config/pipeline.py`

Export implementation:

`export/export_csv.py`

The current configured export list is:

- `listening_history_warehouse`
- `artist_summary`
- `liked_songs`
- `album_listening_sequences`

The export module reads each configured table from MySQL and writes it to CSV under the configured export directory.

Exports use UTF-8 with a byte-order mark to improve compatibility with common spreadsheet and data tools.

### Tableau Public

Tableau Public is the presentation layer.

It consumes the exported datasets to support dashboards, filters, KPI summaries, historical trends, artist and track exploration, and library analysis.

The Python and SQL layers are responsible for data preparation and reusable calculations. Tableau is responsible primarily for visual presentation and dashboard interaction.

---

## 11. ETL Logging and Monitoring

### `etl_log`

The ETL logger records a high-level record for each main pipeline run.

Module:

`load/etl_logger.py`

The current logging schema includes:

- Pipeline name
- Start time
- End time
- Runtime
- Status
- Liked-song download and insert counts
- Recent-track download and insert counts
- Error message

The recent-track fields remain part of the schema even though that stage is currently disabled.

### Run status

The main pipeline distinguishes between:

- `Success`: no reported stage or pipeline errors
- `Warning`: external enrichment commands reported failures, but the pipeline continued
- `Failed`: an exception interrupted the core pipeline

The logger is intended to preserve execution history without making logging failures silently disappear. A database logging error can itself raise an exception.

The external enrichment cache tables provide more detailed per-entity lookup statuses than the high-level ETL log.

---

## 12. Configuration and Runtime Environment

The project is designed for local execution on Windows.

### Runtime

- Python virtual environment: `.venv`
- Main entry point: `main.py`
- Configuration: local environment variables and project configuration modules
- Database: MySQL `spotify_analysis`
- Scheduling: Windows Task Scheduler

### Secrets

API credentials and database credentials are supplied through local environment configuration. Real secrets must not be committed to source control.

The Last.fm module requires `LASTFM_API_KEY`. Other integrations use the configuration expected by their respective modules.

### Scheduling

Windows Task Scheduler can launch the main ETL on a recurring schedule.

The schedule should account for the duration of a full warehouse rebuild and any outstanding external metadata queues. A first-time enrichment backfill may be substantially longer than subsequent runs.

Avoid running the same standalone enrichment job concurrently with its corresponding stage in `main.py`, since both processes may attempt to work on the same eligible records.

---

## 13. Architectural Decisions

The main design principles are:

### Preserve raw source data

Keep the imported listening history separate from cleaned analytical records so transformation logic can be revised and rerun.

### Separate responsibilities

Use independent modules for extraction, metadata loading, transformation, enrichment, analytics, and export.

### Cache external metadata

Persist enrichment results and lookup statuses to avoid unnecessary repeated requests.

### Use conservative identity matching

Store match status and confidence where available rather than assuming that similar titles always represent the same recording.

### Centralize analytical logic

Use reusable transformation and SQL logic to keep reporting consistent across Tableau views.

### Prefer reproducibility over premature optimization

The current warehouse rebuild strategy is straightforward to validate and maintain. Incremental loading can be introduced later if its complexity and benefits justify the change.

---

## 14. Current Boundaries and Future Work

The current architecture provides a complete path from source ingestion through external enrichment and Tableau exports.

Potential future work includes:

- Incremental warehouse loading
- More advanced identity resolution
- Additional metadata sources
- More detailed lookup-level monitoring
- Expanded analytics and recommendation features
- Automated playlist generation

These are future directions rather than claims about the current implementation.

For the implementation status of planned work, consult `roadmap.md`. For the structure of individual tables, consult `data_dictionary.md`. For the rationale behind technical choices, consult `design_decisions.md`.

