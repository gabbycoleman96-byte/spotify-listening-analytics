# Data Dictionary

## Purpose

This document describes the structure of the Spotify Listening Analytics database.

It serves as the primary reference for understanding every table used throughout the project, including how each table is populated, its intended purpose, and how it supports downstream analytics.

---

# Database Overview

The project consists of three types of tables:

1. **Operational Tables** – Used during ETL processing.
2. **Warehouse Tables** – Permanent storage for listening history.
3. **Analytics Tables** – Derived datasets optimized for Tableau Public.

```text
Operational
────────────
liked_songs
recent_50_tracks_snapshot
etl_log

        │

        ▼

Warehouse
────────────
spotify_listening_warehouse

        │

        ▼

Analytics
────────────
artist_discovery
artist_loyalty
forgotten_favorites
listening_session_summary
repeat_behavior
```

---

# Operational Tables

---

## liked_songs

### Purpose

Stores every song currently saved in the user's Spotify library.

This table is refreshed incrementally using the Spotify Web API.

### Population Method

Spotify Web API

### Primary Key

```text
spotify_id
```

### Key Columns

| Column | Description |
|----------|-------------|
| spotify_id | Unique Spotify track ID |
| track_name | Song title |
| artist_name | Primary artist |
| album_name | Album title |
| added_at | Date the song was liked |
| spotify_uri | Spotify URI |

### Used By

- Warehouse enrichment
- Library analytics
- Tableau dashboards

---

## recent_50_tracks_snapshot

### Purpose

Temporary snapshot of Spotify's **Recently Played** endpoint.

This table mirrors the API response and is completely replaced during every ETL run.

### Population Method

Spotify Web API

### Refresh Frequency

Every 30 minutes

### Characteristics

- Temporary
- Replace-on-refresh
- Debugging layer
- Source for incremental warehouse updates

### Used By

- Warehouse updates
- ETL validation

---

## etl_log

### Purpose

Stores execution history for every ETL run.

### Population Method

Python ETL

### Typical Information

- Start time
- End time
- Runtime
- Rows processed
- Rows inserted
- Errors
- Status

---

# Warehouse

---

## spotify_listening_warehouse

### Purpose

The central warehouse and single source of truth for the project.

Every listening event is stored exactly once in this table.

All downstream analytics originate from this dataset.

### Population Method

Historical Spotify Export

+

Incremental Spotify Web API updates

### Primary Key

```text
played_at
spotify_id
```

### Grain

One row = One listening event

### Key Columns

| Column | Description |
|----------|-------------|
| played_at | Timestamp of playback |
| date | Calendar date |
| year | Calendar year |
| quarter | Calendar quarter |
| month_number | Month number |
| month_name | Month name |
| week | ISO week |
| day | Day of month |
| weekday_number | Day of week |
| weekday_name | Day name |
| hour | Hour (24-hour) |
| hour_label | Hour formatted for visualization |
| time | Time component |
| ms_played | Milliseconds listened |
| duration_ms | Track duration (future enrichment) |
| shuffle_state | Shuffle enabled |
| skipped | Track skipped |
| track_name | Song title |
| artist_name | Primary artist |
| album_name | Album title |
| spotify_id | Spotify track ID |
| spotify_uri | Spotify URI |
| is_liked | Currently saved in library |
| primary_genre | Future enrichment |
| secondary_genre | Future enrichment |
| album_art_url | Future enrichment |
| dominant_color | Future enrichment |
| source | Spotify Export or Spotify API |
| imported_at | Warehouse insertion timestamp |

### Used By

Every analytics table.

---

# Analytics Tables

These tables are rebuilt automatically during every ETL run.

---

## artist_discovery

### Purpose

Measures when artists first appeared and tracks long-term discovery trends.

### Source

spotify_listening_warehouse

### Used By

Artist dashboard

---

## artist_loyalty

### Purpose

Measures listening concentration and long-term engagement for each artist.

Typical metrics include:

- Total streams
- Total listening time
- Years active
- Loyalty indicators

### Source

spotify_listening_warehouse

### Used By

Artist dashboard

---

## forgotten_favorites

### Purpose

Identifies artists that were heavily played historically but have seen little or no recent listening activity.

This table highlights changing listening habits over time.

### Source

spotify_listening_warehouse

### Used By

Discovery dashboard

---

## listening_session_summary

### Purpose

Groups consecutive listening events into sessions for behavioral analysis.

Potential metrics include:

- Session duration
- Number of tracks
- Total listening time

### Source

spotify_listening_warehouse

### Used By

Listening Behavior dashboard

---

## repeat_behavior

### Purpose

Measures repeat listening habits across tracks and artists.

Examples include:

- Consecutive plays
- Repeat frequency
- Replay behavior

### Source

spotify_listening_warehouse

### Used By

Listening Behavior dashboard

---

# Data Flow

```text
Spotify Export
        │
        ▼
Warehouse

Spotify API
        │
        ▼
Snapshot
        │
        ▼
Warehouse

Warehouse
        │
        ▼
Analytics Tables
        │
        ▼
CSV Export
        │
        ▼
Tableau Public
```

---

# Data Retention

| Table | Retention |
|---------|-----------|
| liked_songs | Current library |
| recent_50_tracks_snapshot | Latest API snapshot only |
| spotify_listening_warehouse | Permanent |
| Analytics Tables | Fully rebuilt every ETL run |
| etl_log | Permanent |

---

# Future Schema Enhancements

Planned for Version 1.1

- Genre enrichment
- Album artwork URLs
- Dominant album colors
- Track popularity
- Explicit flag
- Release year

These enhancements will be added through Spotify Web API enrichment without changing the warehouse design.