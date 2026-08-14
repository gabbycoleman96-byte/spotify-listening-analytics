# Spotify Listening Analytics

> An end-to-end personal Spotify data engineering and analytics project that collects listening history, transforms it into a MySQL warehouse, enriches the data, and powers a Tableau Public dashboard.

![Pipeline](https://img.shields.io/badge/pipeline-1.0.0-success)
![Warehouse](https://img.shields.io/badge/warehouse-1.1-blue)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.x-orange)
![Tableau](https://img.shields.io/badge/Tableau-Public-blue)

---

## Current Status

**Dashboard completion phase**

The core ETL pipeline is operational and has been running successfully on a recurring schedule. The current priority is finishing the Tableau Public dashboard rather than adding new infrastructure.

The project currently contains:

- A permanent raw Spotify listening-history table
- A transformed listening-history warehouse
- Spotify metadata enrichment
- Data-quality and anomaly flags
- Calendar and listening-behavior dimensions
- SQL analytics
- Tableau-ready exports
- Automated ETL execution
- A multi-page Tableau Public dashboard

Infrastructure improvements are intentionally deferred until the dashboard is complete.

---

# Overview

Spotify Listening Analytics began as a Tableau dashboard project and evolved into a small personal data platform.

The project uses Spotify Extended Streaming History as the authoritative historical listening source and stores the data in MySQL. Python handles extraction, cleaning, transformation, enrichment, loading, analytics, and export.

```text
Spotify Extended Streaming History
                │
                ▼
       listening_history_raw
                │
                ▼
       Cleaning / Transform
                │
                ├── duplicate removal
                ├── impossible-play detection
                ├── offline timestamp correction
                ├── calendar dimensions
                └── metadata enrichment
                │
                ▼
    listening_history_warehouse
                │
        ┌───────┴────────┐
        ▼                ▼
   SQL Analytics     Tableau Export
                         │
                         ▼
                   Tableau Public
```

---

# Project Goals

The project demonstrates practical skills in:

- Data engineering and ETL design
- Relational data warehousing
- Python data transformation
- SQL analytics
- Data quality and anomaly detection
- API and historical-export integration
- Tableau dashboard development
- Workflow automation
- Technical documentation

The end goal is a portfolio-quality analytics product built from real personal listening data rather than a static sample dataset.

---

# Repository Structure

```text
spotify-listening-analytics/

├── api/
├── config/
├── data/
├── extract/
├── load/
├── sql/
│   ├── schema/
│   ├── analytics/
│   └── archive/
├── transform/
├── utils/
├── testers/
│
├── main.py
├── combine_streaming_history.py
├── requirements.txt
├── README.md
└── documentation/
```

The exact repository contents may evolve, but the project is organized around extraction, loading, transformation, SQL analytics, testing, and exports.

---

# ETL Pipeline

The current pipeline is executed automatically using Windows Task Scheduler.

The recurring pipeline is intentionally focused on maintaining the warehouse and dashboard data. The previous 30-minute Recently Played workflow has been retired from the current design.

Typical run:

1. Process available Spotify listening history.
2. Load or refresh the raw listening-history table.
3. Build and clean the warehouse DataFrame.
4. Apply metadata enrichment.
5. Add data-quality and anomaly flags.
6. Load `listening_history_warehouse`.
7. Rebuild SQL analytics.
8. Export Tableau-ready data.
9. Record execution results.

The warehouse is currently rebuilt during each run. This is a deliberate **Version 1 stability choice**. Incremental warehouse rebuilding is deferred to a future version.

---

# Data Sources

## Spotify Extended Streaming History

The historical Spotify export is the primary source for listening events.

The current combined export contains approximately **824,845 raw records**, spanning:

```text
2014-07-04 → 2026-08-07
```

The raw table preserves Spotify's source fields so that transformations can be re-run without modifying the original data.

## Spotify Web API

The API is used primarily for metadata and library enrichment.

The project no longer depends on the Recently Played endpoint as a required recurring source for the dashboard warehouse.

---

# Data Quality

The transformation layer applies several cleaning rules before loading the warehouse.

### Exact duplicate removal

Rows identical across the relevant raw Spotify playback fields are removed.

### Duplicate-play removal

Multiple records sharing the same timestamp and Spotify track are treated as duplicate representations of one playback event. The record with the greatest `ms_played` is retained.

### Impossible-play removal

Playback events that overlap an earlier valid playback of the same track beyond the configured tolerance are removed.

### Anomaly flagging

Suspicious repeating playback patterns are flagged rather than silently deleted.

Current anomaly fields include:

- `is_anomaly`
- `anomaly_type`

This allows Tableau to exclude or analyze questionable records without destroying the underlying historical evidence.

### Offline playback correction

Spotify's `offline_timestamp` is used when an offline playback has a valid timestamp.

The export contains both Unix-second and Unix-millisecond timestamp values, so the transformation determines the appropriate unit from the timestamp magnitude before deriving `played_at` and its date/time dimensions.

---

# Warehouse

The primary analytical table is:

```text
listening_history_warehouse
```

Its grain is:

> One row = one listening event retained after transformation.

The warehouse contains playback timestamps, calendar dimensions, track/artist/album information, Spotify identifiers, listening behavior, metadata, navigation/session fields, and data-quality flags.

The raw source table is:

```text
listening_history_raw
```

The raw table is never modified by warehouse cleaning.

---

# Tableau Public Dashboard

The dashboard is designed with Spotify-inspired visual styling and is the primary presentation layer.

Current dashboard areas include:

- Home
- Artists / Headliners
- Tracks & Albums
- Discovery
- Library Cleanup
- Mobile / Now Playing

The dashboard includes KPI cards, historical listening trends, artist and track analysis, daily/hourly listening patterns, "On This Day" analysis, and persistent Now Playing-style elements.

The dashboard is the current project priority.

---

# Technology Stack

### Languages

- Python
- SQL

### Database

- MySQL 8

### Python Libraries

- pandas
- SQLAlchemy
- requests
- python-dotenv
- tqdm

### Visualization

- Tableau Public

### Automation

- Windows Task Scheduler

---

# Future Work

Future engineering work is intentionally deferred.

Potential Version 2 improvements include:

- Incremental warehouse loading
- More sophisticated album/track identity handling
- Expanded metadata enrichment
- More advanced anomaly detection
- Improved pipeline performance
- Additional external music data sources
- Automated playlist generation
- Direct Spotify playlist creation

These are ideas for later. They are **not current blockers** for Dashboard Version 1.0.0.

---

# Documentation

The project documentation is maintained alongside the codebase:

- `README.md` – Project overview and current state
- `architechture.md` – System architecture and data flow
- `CHANGELOG.md` – Major changes and milestones
- `data_dictionary.md` – Database and warehouse reference
- `design_decisions.md` – Architectural and technical reasoning
- `project_journal.md` – Development history and lessons learned
- `roadmap.md` – Current priorities and deferred work

---

# Author

**Gabby Coleman**

Career Coach transitioning into Data Analytics and Data Engineering.

---

# License

This project is provided for educational and portfolio purposes.
