# Data Dictionary

## Purpose

This document describes the current database structure used by Spotify Listening Analytics.

The documentation distinguishes between raw source data, the transformed warehouse, and downstream analytics.

---

# Database Overview

```text
Raw
────────────────────────
listening_history_raw
        │
        ▼
Transformation
        │
        ▼
Warehouse
────────────────────────
listening_history_warehouse
        │
        ├───────────────┐
        ▼               ▼
SQL Analytics      Tableau Exports
```

---

# Raw Table

## `listening_history_raw`

### Purpose

Preserves the combined Spotify Extended Streaming History in MySQL so the warehouse can be rebuilt without modifying the source data.

### Grain

One row = one Spotify source playback record.

### Important Columns

| Column | Description |
|---|---|
| `raw_id` | Auto-incrementing database identifier |
| `ts` | Spotify source playback/sync timestamp |
| `platform` | Spotify playback platform |
| `ms_played` | Milliseconds Spotify recorded |
| `conn_country` | Country associated with the playback connection |
| `ip_addr` | Source IP from Spotify export |
| `master_metadata_track_name` | Spotify track name |
| `master_metadata_album_artist_name` | Spotify album artist |
| `master_metadata_album_album_name` | Spotify album name |
| `spotify_track_uri` | Spotify track URI |
| `episode_name` | Podcast episode, when applicable |
| `episode_show_name` | Podcast show, when applicable |
| `spotify_episode_uri` | Podcast episode URI |
| `reason_start` | Spotify playback-start reason |
| `reason_end` | Spotify playback-end reason |
| `shuffle` | Whether shuffle was enabled |
| `skipped` | Whether Spotify marked the record as skipped |
| `offline` | Whether Spotify marked the playback as offline |
| `offline_timestamp` | Offline playback timestamp when provided |
| `incognito_mode` | Whether incognito mode was enabled |
| `source` | Source label for the imported record |

The raw table may contain additional Spotify export fields. It is intentionally closer to Spotify's source schema than the warehouse.

---

# Warehouse

## `listening_history_warehouse`

### Purpose

The central analytical table and primary source for Tableau.

### Grain

One row = one listening event retained after cleaning and transformation.

### Current Scale

Approximately **804,193 retained listening events** after the current cleaning rules are applied to the 824,845-row raw export.

### Canonical Timestamp

```text
played_at
```

For valid offline records, `played_at` may be derived from `offline_timestamp` rather than Spotify's `ts`.

### Calendar / Time Dimensions

| Column | Description |
|---|---|
| `played_at` | Canonical playback timestamp |
| `date` | Calendar date |
| `year` | Calendar year |
| `quarter` | Calendar quarter |
| `month_number` | Month number |
| `month_name` | Month name |
| `week` | ISO week |
| `day` | Day of month |
| `weekday_number` | Day-of-week number |
| `weekday_name` | Day name |
| `hour` | Hour of day |
| `hour_label` | Display-friendly hour |
| `time` | Time component |

### Listening Fields

| Column | Description |
|---|---|
| `ms_played` | Milliseconds listened |
| `seconds` | Listening duration in seconds |
| `track_name` | Track title |
| `artist_name` | Artist name |
| `album_name` | Album name |
| `shuffle` | Shuffle state |
| `skipped` | Skip indicator |
| `is_liked` | Whether the track is currently liked |

### Spotify Identifiers

| Column | Description |
|---|---|
| `spotify_id` | Spotify track ID |
| `spotify_uri` | Spotify track URI |
| `album_art_url` | Album artwork URL used by the dashboard |

For current dashboard work, the album artwork URL is sufficient as the practical album-art identifier. A more formal album identity model is deferred.

### Metadata / Enrichment

Current metadata/enrichment fields include the project's available track metadata such as:

- Track length
- Primary genre
- Secondary genre
- Album artwork
- Dominant album color

The exact enrichment set may grow as the metadata pipeline evolves.

### Behavioral / Navigation Fields

The warehouse also contains derived fields used by the dashboard and listening analysis, including play-number, navigation, session, and timing-related calculations.

Examples include:

- Previous track
- Seconds since previous play
- Track/artist play numbering
- Session/navigation fields

These fields are derived by the transformation/enrichment layer and are not Spotify source fields.

### Data Quality Fields

| Column | Description |
|---|---|
| `is_anomaly` | Flags a playback record requiring data-quality consideration |
| `anomaly_type` | Describes the detected anomaly |

Current anomaly detection includes repeating playback loops.

---

# Cleaning Rules

The warehouse transformation currently applies these rules:

1. Remove exact duplicates across the relevant Spotify playback fields.
2. Remove duplicate plays sharing the same `ts` and Spotify track URI, retaining the record with the greatest `ms_played`.
3. Remove impossible overlapping playback of the same track beyond the configured tolerance.
4. Correct offline playback timestamps when Spotify supplies a usable `offline_timestamp`.
5. Add data-quality flags for suspicious repeating playback patterns.
6. Remove rows that lack required track metadata.

Cleaning happens in memory. The raw table is never modified.

---

# Analytics

The project has SQL analytics used by the Tableau dashboard.

Analytics are rebuilt from the warehouse rather than treated as a second source of truth.

The exact analytics table set is allowed to evolve with the dashboard and is documented in the SQL layer as it changes.

---

# Data Retention

| Layer | Retention |
|---|---|
| `listening_history_raw` | Permanent source copy |
| `listening_history_warehouse` | Permanent analytical warehouse |
| Analytics outputs | Rebuilt from warehouse |
| ETL logs | Execution history |

---

# Important Data Semantics

## Playback Count

A warehouse row represents a retained playback event, not necessarily a perfect reconstruction of a human intentionally pressing Play.

Spotify's export can contain unusual playback records, including repeated loops and offline synchronization behavior. The project therefore preserves anomaly information instead of pretending every record is equally trustworthy.

For Tableau KPIs, anomaly records can be excluded where appropriate.

## Offline Playback

`offline_timestamp` is not assumed to have one universal unit across the entire export.

The transformation distinguishes seconds-scale and milliseconds-scale Unix timestamps before converting them.

This prevents offline synchronization timestamps from distorting daily, hourly, and historical listening metrics.
