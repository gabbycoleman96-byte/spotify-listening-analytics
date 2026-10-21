# Spotify Listening Analytics

A personal music data engineering and analytics project that transforms Spotify listening history into a structured MySQL warehouse, enriches tracks and artists with external music metadata, and powers interactive Tableau Public dashboards.

**Repository:** [spotify-listening-analytics](https://github.com/gabbycoleman96-byte/spotify-listening-analytics)

![Python](https://img.shields.io/badge/Python-3.x-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.x-orange)
![Tableau](https://img.shields.io/badge/Tableau-Public-blue)
![Status](https://img.shields.io/badge/Project-Active-success)

---

## Project Overview

Spotify Listening Analytics began as a dashboard built around personal listening history. It has evolved into a modular data engineering project with historical data ingestion, ETL orchestration, relational data modeling, metadata enrichment, quality controls, SQL analytics, and Tableau-ready exports.

The project combines personal listening records with track, artist, album, release, and community-supplied music metadata. The goal is to explore listening habits while building a reusable foundation for music discovery, library analysis, and future playlist-generation tools.

### Core capabilities

- Import Spotify Extended Streaming History into MySQL.
- Preserve raw listening records for reproducible transformations.
- Clean and transform listening events into an analytical warehouse.
- Maintain Spotify track, artist, album, and canonical song identity metadata.
- Enrich track release information through MusicBrainz.
- Enrich track and artist metadata and tags through Last.fm.
- Track data-quality issues and flag suspicious playback patterns.
- Generate SQL analytics and Tableau-ready CSV exports.
- Automate recurring ETL execution with Windows Task Scheduler.
- Record pipeline execution status, runtime, and errors.

---

## Architecture

```text
Spotify Extended Streaming History
                 |
                 v
       Raw Listening History
        listening_history_raw
                 |
                 v
       Python ETL Orchestration
                 |
       +---------+----------+
       |                    |
       v                    v
 Spotify Metadata      External Enrichment
 Track / Artist /      MusicBrainz / Last.fm
 Album / Identity            |
       |                     v
       |              External Metadata Cache
       |              Tags / Release Metadata
       |                     |
       +----------+----------+
                  |
                  v
       Warehouse Transformation
       Cleaning / Time Dimensions
       Identity Mapping / Quality Flags
                  |
                  v
       listening_history_warehouse
                  |
           +------+------+
           |             |
           v             v
      SQL Analytics   Tableau Exports
                          |
                          v
                    Tableau Public
```

The warehouse is rebuilt from the available historical source data during a normal pipeline run. External metadata is stored in dedicated cache tables rather than being treated as part of the raw Spotify source.

---

## Technology Stack

| Area | Technologies |
|---|---|
| Programming | Python |
| Data processing | pandas |
| Database | MySQL 8 |
| Database access | SQLAlchemy, MySQL Connector |
| APIs | Spotify Web API, MusicBrainz, Last.fm |
| HTTP requests | requests |
| Configuration | python-dotenv |
| Analytics | SQL |
| Visualization | Tableau Public |
| Automation | Windows Task Scheduler |
| Version control | Git and GitHub |

---

## Repository Structure

```text
spotify-listening-analytics/
├── api/                         # API clients and related assets
├── config/                      # Pipeline and export configuration
├── data/                        # Local source and intermediate data
├── docs/                        # Project documentation
├── export/                      # Tableau dataset exports
├── extract/                     # Spotify data extraction
├── load/                        # Database loading and enrichment
│   ├── database.py
│   ├── etl_logger.py
│   ├── load_artist_metadata.py
│   ├── load_track_metadata.py
│   ├── enrich_musicbrainz_tracks.py
│   └── enrich_lastfm.py
├── sql/
│   ├── schema/                  # Database table definitions
│   ├── analytics/               # Reusable analytical SQL
│   └── archive/                 # Retired or archived SQL
├── transform/                   # Warehouse and identity transforms
├── utils/                        # Supporting utilities and workflows
├── testers/                     # Testing and investigation scripts
├── main.py                       # Main ETL orchestrator
├── combine_streaming_history.py
├── requirements.txt
└── README.md
```

This is a conceptual guide to the principal modules. Individual scripts and supporting files may evolve as the project develops.

---

## Data Sources

### Spotify Extended Streaming History

Spotify's historical export is the primary source for personal listening events.

The export is combined and loaded into:

`listening_history_raw`

The raw table preserves the imported playback records so transformation rules can be revised without modifying the original database source.

Historical record counts and coverage dates change when a newer Spotify export is imported. Consult the current database and project journal for the latest validated totals.

### Spotify Web API

The Spotify API supplies metadata and library information used by the pipeline, including track and artist attributes.

The project also maintains canonical Spotify song identities to connect duplicate or alternate Spotify track records where the identity logic supports a match.

### MusicBrainz

MusicBrainz supplies external recording and release metadata.

The track enrichment process uses ISRC lookups, artist credits, title similarity, and duration evidence to evaluate potential recording matches. It records match status and confidence rather than assuming every candidate is correct.

Track enrichment is implemented in:

`load/enrich_musicbrainz_tracks.py`

### Last.fm

Last.fm supplies community music metadata, including track and artist tags, listener and play counts, and available descriptions.

Last.fm's listeners and play counts are community-wide statistics. They are **not** the user's personal Spotify listening totals.

The Last.fm enrichment process is implemented in:

`load/enrich_lastfm.py`

External enrichment results are stored in separate cache tables. Existing Spotify metadata, canonical song identities, and listening history are not directly overwritten by these enrichment scripts.

---

## Database Design

### Raw listening history

`listening_history_raw`

Stores imported Spotify playback records and serves as the source for warehouse rebuilding.

### Analytical warehouse

`listening_history_warehouse`

The primary analytical table used for listening-history analysis and Tableau reporting.

Its intended grain is one retained listening event per row after the project's transformation and data-quality rules.

### Spotify metadata and identity

The project maintains separate metadata structures for tracks, artists, albums, track-to-artist relationships, and canonical song identities. These support consistent joins and help distinguish Spotify catalog entries from the underlying song or recording.

### External metadata cache

The external enrichment schema includes:

| Table | Purpose |
|---|---|
| `musicbrainz_track_metadata` | MusicBrainz recording matches and release dates |
| `musicbrainz_artist_metadata` | MusicBrainz artist identity metadata |
| `lastfm_track_metadata` | Last.fm track metadata and community statistics |
| `lastfm_artist_metadata` | Last.fm artist metadata and community statistics |
| `external_track_tags` | Source-attributed tags for tracks |
| `external_artist_tags` | Source-attributed tags for artists |
| `lastfm_similar_tracks` | Storage for Last.fm similar-track results |

The cache tables track lookup status and timestamps so successful lookups can be reused instead of repeatedly requesting the same metadata.

Database table definitions are maintained under `sql/schema/`.

---

## ETL Pipeline

The main entry point is:

```powershell
python main.py
```

The current orchestration runs the following stages:

1. Check for and load new liked songs.
2. Rebuild the listening-history warehouse.
3. Rebuild the permanent song identity map.
4. Apply canonical Spotify song identities.
5. Retrieve metadata for missing artists.
6. Retrieve metadata for tracks.
7. Run external music metadata enrichment.
8. Update album artwork.
9. Rebuild warehouse enrichment.
10. Rebuild analytics tables.
11. Export Tableau datasets.
12. Record execution results in the ETL log.

The Recently Played stage remains present in the code but is currently disabled in the main orchestration.

### External enrichment orchestration

The external enrichment stage invokes the standalone enrichment scripts for:

- MusicBrainz track metadata
- Last.fm track metadata
- Last.fm artist metadata

The scripts manage their own API requests, rate limiting, lookup queues, and cache writes.

The enrichment process is designed to work through eligible records while reusing cached successful lookups. The initial historical backfill may take considerably longer than later runs that have only a small number of new records.

External enrichment warnings are intended to remain distinguishable from failures in the core ETL workflow.

### Warehouse strategy

The warehouse is rebuilt during the normal ETL process rather than incrementally updated one event at a time.

This approach keeps transformation behavior reproducible and straightforward to inspect. Incremental processing and performance optimization remain potential future improvements.

---

## Data Quality and Transformation

The transformation layer handles source inconsistencies before data reaches downstream analytics.

### Duplicate handling

The project distinguishes exact duplicate records from records that share a timestamp and track identity. Where the configured rules identify duplicate representations of a playback event, the retained record is selected using the project's playback-duration logic.

### Impossible playback

Playback events that violate the project's overlap rules can be excluded during transformation.

### Anomaly flags

Suspicious repeating playback patterns can be flagged instead of silently deleting all questionable historical evidence.

The warehouse includes fields such as:

- `is_anomaly`
- `anomaly_type`

These allow downstream analytics to filter suspicious records where appropriate.

### Offline playback timestamps

When a valid offline playback timestamp is available, the transformation can use it to derive the canonical playback time rather than relying solely on the source synchronization timestamp.

Timestamp-unit handling is necessary because exported offline timestamp values may use different Unix timestamp scales.

### Canonical song identity

Spotify can contain multiple catalog entries for the same underlying song. The project uses identity mapping to support consistent analysis across these entries without assuming that every alternate version is interchangeable.

---

## Analytics and Tableau

The SQL analytics layer provides reusable calculations for downstream reporting.

The configured Tableau export list is maintained in:

`config/pipeline.py`

Current configured exports include:

- `listening_history_warehouse`
- `artist_summary`
- `liked_songs`
- `album_listening_sequences`

The export module writes the configured datasets for use in Tableau Public.

The dashboard is designed around Spotify-inspired styling, listening-history exploration, artist and track analysis, and library insights. Dashboard pages and their implementation status are maintained separately from the ETL documentation.

---

## Setup

These instructions assume a local Windows development environment with Python and MySQL installed.

### 1. Clone the repository

```powershell
git clone https://github.com/gabbycoleman96-byte/spotify-listening-analytics.git
cd spotify-listening-analytics
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file using the variable names expected by the database connection and Spotify API configuration.

The project uses environment variables for database credentials and API configuration. Last.fm enrichment additionally requires:

```text
LASTFM_API_KEY=your_lastfm_api_key
```

Keep real credentials in the local `.env` file. Do not commit secrets to GitHub or paste them into public issues.

Check the repository's database and API configuration modules for the complete set of required environment variable names.

### 5. Prepare the database

Create the `spotify_analysis` database and apply the required schema scripts under `sql/schema/` in the appropriate dependency order.

The external metadata tables must exist before the MusicBrainz and Last.fm enrichment scripts can write results to them.

Do not recreate or truncate existing tables as a routine setup step on a database containing data you want to preserve.

### 6. Prepare source data

Place the required Spotify Extended Streaming History export files in the configured local source directory. Follow the export update instructions in:

`utils/new_spotify_export/spotify_export_update_instructions.md`

Use the documented backup and import process when replacing an existing historical export.

### 7. Run the pipeline

```powershell
python main.py
```

The first full run may take significantly longer than later runs because it may need to load historical data, build metadata, and perform external enrichment.

---

## Running External Enrichment Separately

The enrichment modules can also be run independently for testing, backfills, and troubleshooting.

### MusicBrainz tracks

Process a small batch:

```powershell
python -m load.enrich_musicbrainz_tracks --limit 10
```

Process all eligible tracks:

```powershell
python -m load.enrich_musicbrainz_tracks --all
```

### Last.fm tracks

```powershell
python -m load.enrich_lastfm --entity tracks --limit 10
```

Process all eligible tracks:

```powershell
python -m load.enrich_lastfm --entity tracks --all
```

### Last.fm artists

```powershell
python -m load.enrich_lastfm --entity artists --limit 10
```

Process all eligible artists:

```powershell
python -m load.enrich_lastfm --entity artists --all
```

Start with a small batch when validating a new setup. Large backfills can take hours because the scripts deliberately limit request frequency.

Avoid running a standalone backfill concurrently with the same enrichment stage in `main.py`, since both processes could attempt to handle the same pending records.

---

## Automation and Logging

The pipeline is designed to run locally and can be scheduled with Windows Task Scheduler.

The ETL logger records high-level execution information, including start and end times, runtime, status, liked-song counts, recent-track counts when that stage is used, and error details.

The external enrichment stage can report warnings separately from core pipeline exceptions. Individual lookup statuses are also stored in the enrichment cache tables.

A scheduled run should be monitored when introducing schema changes, updating credentials, replacing source exports, or making significant ETL changes.

---

## Project Documentation

The `docs/` directory contains the supporting documentation:

| Document | Purpose |
|---|---|
| `docs/architecture.md` | System components, data flow, and ETL stages |
| `docs/data_dictionary.md` | Database tables, grains, and important fields |
| `docs/design_decisions.md` | Rationale behind key technical choices |
| `docs/CHANGELOG.md` | Significant changes and milestones |
| `docs/project_journal.md` | Development history and lessons learned |
| `docs/roadmap.md` | Current priorities and future plans |

The source code and database schema are the authoritative references for implementation details. Documentation should distinguish implemented behavior from planned features and historical checkpoints.

---

## Future Directions

Potential future improvements include:

- Incremental warehouse processing and performance optimization
- More complete track, album, and artist identity resolution
- Additional data-quality validation
- More advanced listening-session and discovery analytics
- Using external tags and release metadata for music exploration
- Generating decade-based and mood-based playlists
- Evaluating existing playlists against metadata-derived themes
- Optional automated playlist creation through Spotify

These are future directions, not claims that every feature is currently implemented.

---

## Project Goals

This project is both a personal music analytics tool and a practical data engineering portfolio project.

It demonstrates work with:

- ETL pipeline design and orchestration
- API integration and rate-limited data collection
- Relational database design
- Data cleaning and validation
- Entity resolution and canonical identities
- Metadata caching and enrichment
- SQL analytics
- Data visualization and dashboard design
- Workflow automation
- Technical documentation and version control

---

## Author

Gabby Coleman

A personal data engineering and music analytics project.

