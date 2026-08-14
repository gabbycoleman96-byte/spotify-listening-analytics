# Architecture

## Purpose

Spotify Listening Analytics uses a warehouse-first architecture that separates raw data preservation, transformation, enrichment, storage, analytics, and visualization.

The current architecture prioritizes **stability and dashboard completion**. The warehouse is rebuilt from the raw listening history during each pipeline run. Incremental warehouse processing is intentionally deferred.

---

# System Overview

```text
                 Spotify Extended Streaming History
                               │
                               ▼
                    listening_history_raw
                               │
                               ▼
                    Warehouse Transformation
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
       Cleaning          Date Dimensions       Enrichment
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                 listening_history_warehouse
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              SQL Analytics        Tableau Exports
                                          │
                                          ▼
                                    Tableau Public
```

---

# Layers

## 1. Source Layer

### Spotify Extended Streaming History

The historical Spotify export is the authoritative source for listening events.

Multiple JSON files are combined into:

```text
data/Spotify_json_files/listening_history_raw.csv
```

The current combined export contains approximately 824,845 records covering July 4, 2014 through August 7, 2026.

---

# 2. Raw Database Layer

### `listening_history_raw`

This table stores the imported Spotify history with minimal transformation.

Important characteristics:

- Preserves Spotify source fields
- Provides a reproducible source for warehouse rebuilding
- Is not modified by warehouse cleaning
- Contains `source` metadata

This separation allows transformation rules to change without requiring another Spotify export.

---

# 3. Transformation Layer

Location:

```text
transform/
```

The transformation layer builds the warehouse DataFrame.

### Cleaning

Current rules include:

1. Remove exact duplicate records.
2. Remove duplicate plays sharing the same timestamp and Spotify track.
3. Remove impossible overlapping playback events.
4. Normalize values where required.

### Playback Timestamp Correction

For offline records:

```text
offline = true
+
offline_timestamp is present
```

the offline timestamp is used as the playback timestamp.

Spotify's export contains both seconds- and milliseconds-scale Unix timestamps. The transformation detects the scale before conversion.

`played_at` is then treated as the canonical timestamp from which calendar and time-of-day dimensions are derived.

### Metadata

Track metadata and other warehouse enrichments are added after cleaning and timestamp normalization.

### Data Quality

Suspicious repeating playback behavior is retained and marked using:

```text
is_anomaly
anomaly_type
```

This preserves the evidence while allowing downstream analytics to exclude questionable records when appropriate.

---

# 4. Warehouse Layer

Primary table:

```text
listening_history_warehouse
```

Grain:

```text
One row = One retained listening event
```

The warehouse is the central source for Tableau and SQL analytics.

Current warehouse processing rebuilds the table from the transformed source data on each pipeline run.

This is intentionally left unchanged for the current dashboard-completion phase.

---

# 5. Analytics Layer

Location:

```text
sql/analytics/
```

SQL analytics are derived from the warehouse.

The analytics layer supports reusable calculations and Tableau-ready reporting.

Business logic that is useful across multiple visualizations is preferably handled upstream rather than duplicated across Tableau worksheets.

---

# 6. Export Layer

The pipeline exports Tableau-ready datasets after warehouse and analytics processing.

CSV exports are used because they are:

- Simple
- Portable
- Easy to inspect
- Compatible with Tableau Public

---

# 7. Presentation Layer

### Tableau Public

Tableau is responsible primarily for:

- Visualization
- Filtering
- Dashboard interaction
- KPI presentation
- Visual storytelling

The current dashboard is the primary project deliverable.

---

# Scheduling

Windows Task Scheduler runs the pipeline on a recurring schedule.

The previous 30-minute Recently Played workflow is no longer part of the current required architecture.

The current schedule is intentionally less frequent because the dashboard warehouse is based primarily on the historical export and the recurring workflow no longer depends on the Recently Played endpoint.

---

# Current Stability Boundary

The following are intentionally **not being refactored during Dashboard Version 1.0.0**:

- Incremental warehouse loading
- Warehouse rebuild optimization
- Major schema redesign
- New data sources
- Large-scale ETL restructuring

The purpose of this boundary is simple: the current pipeline works, so dashboard completion takes priority over architectural optimization.

These improvements belong in a future version.

---

# Architectural Principles

## Single Source of Truth

`listening_history_warehouse` is the central analytical source.

## Preserve Raw Data

The raw Spotify history remains available so transformation logic can be rerun.

## Clean Before Analytics

Data quality and timestamp corrections occur before warehouse analytics.

## Centralize Reusable Logic

Shared business logic should live upstream rather than being recreated across dashboards.

## Avoid Premature Optimization

A working, understandable pipeline is more valuable right now than an optimized pipeline that risks destabilizing the project.
