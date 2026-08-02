# Architecture

## Purpose

The Spotify Listening Analytics project is designed around a warehouse-first architecture that separates data collection, transformation, storage, analytics, and visualization into independent layers.

The primary objective is to create a maintainable ETL pipeline that automatically collects Spotify listening data, stores it in a centralized warehouse, and produces analytics-ready datasets for Tableau Public.

---

# System Overview

```text
                           Spotify
                    Extended Streaming History
                               │
                               ▼
                  import_streaming_history.py
                               │
                               ▼
                spotify_listening_warehouse
                               ▲
                               │
                  dashboard_transform.py
                               ▲
                               │
                 recent_50_tracks_snapshot
                               ▲
                               │
                   Spotify Web API
                               ▲
                               │
                recent_tracks.py
```

Once the warehouse has been updated:

```text
spotify_listening_warehouse
            │
            ▼
      SQL Analytics Layer
            │
            ▼
 Analytics Tables
            │
            ▼
 export_csv.py
            │
            ▼
      Tableau Public
```

---

# Project Structure

```text
spotify_etl/

api/
config/
export/
extract/
load/
sql/
    analytics/
    archive/
    schema/
testers/
transform/
utils/

main.py
requirements.txt
README.md
```

---

# Architectural Principles

The project follows several design principles that keep the codebase modular and maintainable.

## Single Source of Truth

Every listening event exists only once inside the project.

```text
spotify_listening_warehouse
```

All reporting tables are rebuilt from this warehouse.

This prevents duplicate business logic and ensures every visualization references the same underlying data.

---

## Layer Separation

The project is organized into independent ETL stages.

```text
Extract
↓

Transform
↓

Load
↓

Analytics

↓

Export
```

Each stage has one responsibility.

---

# Extract Layer

Location

```text
extract/
```

Purpose

Responsible for retrieving raw data from Spotify.

Components

### import_streaming_history.py

Imports Spotify Extended Streaming History JSON exports.

Responsibilities

- Read JSON files
- Standardize columns
- Create calendar dimensions
- Mark liked songs
- Return a DataFrame

---

### liked_songs.py

Downloads the user's current liked songs.

Responsibilities

- Authenticate with Spotify
- Handle pagination
- Return incremental updates

---

### recent_tracks.py

Downloads the user's most recent listening activity.

Responsibilities

- Call Spotify Recently Played endpoint
- Retrieve the most recent 50 tracks
- Refresh the snapshot table

---

# Transform Layer

Location

```text
transform/
```

Purpose

Converts raw Spotify data into the warehouse schema.

Responsibilities

- Merge historical and API data
- Remove duplicates
- Create warehouse fields
- Prepare data for loading

---

# Load Layer

Location

```text
load/
```

Purpose

Move transformed data into MySQL.

Responsibilities

- Batch inserts
- Duplicate protection
- SQL execution
- Logging

Modules

- loader.py
- database.py
- load_dashboard_data.py

---

# Warehouse

Primary table

```text
spotify_listening_warehouse
```

Purpose

Stores one record for every listening event.

Characteristics

- Append-only
- Historical
- Central source of truth
- Optimized for analytics

---

# Analytics Layer

Location

```text
sql/analytics/
```

Purpose

Generate reusable reporting tables.

Current tables

- artist_discovery
- artist_loyalty
- forgotten_favorites
- listening_session_summary
- repeat_behavior

These tables contain business logic that would otherwise need to be recreated inside Tableau.

---

# Export Layer

Location

```text
export/
```

Purpose

Generate Tableau-ready CSV files.

Responsibilities

- Export warehouse
- Export analytics tables
- Maintain consistent filenames
- Overwrite previous exports

---

# Presentation Layer

Tool

Tableau Public

Responsibilities

- Interactive dashboards
- User filtering
- KPI reporting
- Visual storytelling

The dashboards intentionally contain minimal business logic.

Most calculations are performed upstream inside MySQL.

---

# Scheduling

The ETL pipeline is executed automatically using Windows Task Scheduler.

Typical execution frequency

```text
Every 30 minutes
```

Pipeline sequence

```text
Download liked songs

↓

Download recent tracks

↓

Refresh snapshot

↓

Update warehouse

↓

Rebuild analytics

↓

Export CSVs

↓

Log execution
```

---

# Error Handling

Version 1 includes basic operational safeguards.

- Duplicate protection
- Incremental API downloads
- SQL transaction handling
- Execution logging

Future versions will introduce

- Retry logic
- Enhanced validation
- Notification support

---

# Why This Architecture?

The project originally relied on manually generated summary tables.

As the project evolved, this approach became increasingly difficult to maintain.

Migrating to a warehouse-first architecture provided several advantages.

- One source of truth
- Reusable analytics
- Simpler Tableau dashboards
- Easier feature expansion
- Cleaner project organization

This architecture also closely resembles patterns commonly used in production analytics environments, making the project easier to extend and maintain over time.