# Architecture.md

## Project Overview

The Spotify ETL + Analytics project is a portfolio-quality data
engineering project that automates the ingestion, storage,
transformation, and visualization of Spotify listening data.

### Current Architecture

``` text
Spotify API
      │
      ▼
Python ETL
      │
      ▼
MySQL
      │
      ├── liked_songs
      ├── recent_tracks_snapshot
      ├── listening_history_api
      └── etl_log
      │
      ▼
Analytics SQL
      │
      ▼
Summary Tables
      │
      ▼
CSV Exports
      │
      ▼
Tableau Public
```

## Folder Structure

``` text
spotify_etl/
│
├── api/
├── config/
├── data/
│   ├── raw/
│   ├── processed/
│   └── exports/
├── extract/
├── transform/
├── load/
├── export/
├── sql/
│   ├── schema/
│   └── analysis/
├── utils/
├── main.py
├── requirements.txt
└── README.md
```

## Current Pipeline

1.  Download new liked songs incrementally.
2.  Download latest 50 recent plays.
3.  Refresh recent_tracks_snapshot.
4.  Archive new plays into listening_history_api.
5.  Rebuild analytics tables.
6.  Export Tableau CSV datasets.
7.  Log the ETL execution.


## Warehouse Refactor (In Progress)

The project has begun transitioning from a dual-history architecture to
a single warehouse architecture centered on `dashboard_data`.

Current transition:

``` text
Spotify API
      │
      ▼
recent_tracks_snapshot
      │
      ├── dashboard_data (new warehouse)
      └── recent_tracks_snapshot (debug/snapshot)
```

Future Spotify Extended Streaming History exports will also load
directly into `dashboard_data`, making it the single source of truth.


## Analytics Simplification

The project has retired the first-generation summary tables.

Current target architecture:

Spotify API / Spotify Export ↓ dashboard_data ↓ dashboard_data.csv ↓
Tableau

Specialized SQL tables will only be created when Tableau cannot
efficiently calculate the analysis.
