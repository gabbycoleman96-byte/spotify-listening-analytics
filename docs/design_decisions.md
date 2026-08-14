# Design Decisions

## Purpose

This document records the important technical and architectural decisions behind Spotify Listening Analytics, including decisions made during the current dashboard-completion phase.

The project intentionally favors **stability over unnecessary refactoring** while Version 1 of the dashboard is being completed.

---

# Guiding Principles

- Simplicity over unnecessary complexity.
- Automation over repetitive manual work.
- One analytical source of truth.
- Preserve raw data.
- Centralize reusable logic.
- Maintainability over premature optimization.
- Finish the current version before expanding scope.

---

# Why Build a Data Warehouse?

## Decision

Use a centralized listening-history warehouse rather than maintaining independent summary tables for each visualization.

## Rationale

The project originally relied on many manually maintained summary tables. That approach caused business logic to become scattered across the project.

A warehouse allows new Tableau views and SQL analyses to use the same underlying listening events.

---

# Why Keep a Raw Table?

## Decision

Preserve Spotify's imported history in:

```text
listening_history_raw
```

## Rationale

The raw table provides a stable source from which the warehouse can be rebuilt whenever transformation rules change.

This is particularly important because Spotify's historical export contains quirks that may require new cleaning rules later.

---

# Why Clean in Python?

## Decision

Perform the main cleaning and transformation in an in-memory pandas DataFrame.

## Rationale

Python provides a clear place to implement:

- Duplicate handling
- Timestamp correction
- Calendar dimensions
- Metadata enrichment
- Anomaly detection

The raw MySQL table remains untouched.

---

# Duplicate Strategy

## Exact duplicates

Identical Spotify playback records are removed.

## Same timestamp + same track

Multiple records with the same timestamp and Spotify track are treated as duplicate representations of the same event.

The record with the greatest `ms_played` is retained.

## Why?

Legitimate repeat listening is common, so deduplication must distinguish duplicated records from genuinely separate plays.

---

# Impossible Playback Strategy

## Decision

Remove playback events that overlap an earlier valid playback of the same track beyond the configured tolerance.

## Rationale

A track beginning before the previous playback of that same track could reasonably have finished is considered impossible under the project's playback model.

This is a data-quality rule, not a claim that Spotify's source record itself is invalid.

---

# Anomaly Strategy

## Decision

Do not automatically delete every suspicious listening pattern.

Instead, flag suspicious repeating playback loops with:

```text
is_anomaly
anomaly_type
```

## Rationale

The project needs to distinguish between:

- Data that is definitely duplicate or impossible
- Data that is unusual but could represent real Spotify behavior

The July 5, 2022 repeating playback sequence is the clearest example. It produces hundreds of records for five tracks in a repeating pattern. Those records are now identifiable without silently destroying the historical source.

For dashboard metrics where these records would distort results, the anomaly flag can be used as a filter.

---

# Offline Timestamp Decision

## Decision

When:

```text
offline = true
```

and a valid `offline_timestamp` exists, use the offline timestamp as the canonical `played_at`.

## Rationale

Spotify's `ts` can represent the time an offline playback record was synchronized rather than the actual playback time.

The historical export contains both seconds-scale and milliseconds-scale `offline_timestamp` values. The transformation therefore determines the timestamp unit from its magnitude before conversion.

After correction, all calendar and time-of-day dimensions are derived from `played_at`.

---

# Why `played_at` Is the Canonical Timestamp

All dashboard time dimensions derive from:

```text
played_at
```

This prevents individual worksheets from making different assumptions about whether they should use Spotify's raw `ts` or an offline playback timestamp.

---

# Why Use Album Artwork URL as the Practical Album Identifier?

## Decision

For current dashboard work, the album artwork URL is acceptable as the practical unique identifier for album artwork.

## Rationale

The warehouse already contains album artwork URLs for the enriched tracks, and the dashboard primarily needs a stable way to associate artwork with the relevant album/image.

A formal album dimension or more sophisticated album identity model can be added later if needed.

---

# Why Rebuild the Warehouse?

## Current Decision

The warehouse is currently rebuilt from the transformed raw history during each pipeline run.

## Rationale

It is reliable, easy to reason about, and currently working.

An incremental warehouse strategy would reduce processing time, but implementing it safely requires additional architectural work.

**That optimization is intentionally deferred.**

The current goal is to finish the Tableau dashboard without destabilizing the working ETL.

---

# Why Reduce the ETL Schedule?

## Decision

The recurring pipeline no longer needs to run every 30 minutes.

## Rationale

The project no longer depends on continuously refreshing the Recently Played endpoint as a required source of new listening events.

A lower-frequency schedule is sufficient for the current workflow and reduces unnecessary repeated warehouse processing.

---

# Why Tableau Public?

## Decision

Use Tableau Public as the presentation layer.

## Rationale

The project is intended as a portfolio artifact.

Tableau Public makes the finished dashboard easy to share while allowing the data-engineering work to remain the foundation behind it.

---

# Why CSV Exports?

CSV exports provide a simple bridge between MySQL/Python and Tableau Public.

Benefits:

- Portable
- Easy to inspect
- Tableau-compatible
- Easy to replace after each ETL run
- No live database infrastructure required for Tableau Public

---

# Current Stability Boundary

During Dashboard Version 1.0.0, the following are explicitly considered **out of scope unless they become necessary to finish the dashboard**:

- Warehouse incremental loading
- Major schema redesign
- New external data sources
- Broad ETL refactoring
- Performance optimization
- Playlist automation
- Additional enrichment that does not support a dashboard requirement

The principle is:

> If the current system works and the dashboard can be finished without changing it, leave it alone.

---

# Versioning Philosophy

## Pipeline Version 1.0.0

Established the working automated ETL and warehouse architecture.

## Warehouse Version 1.1

Adds the current enrichment, data-quality, anomaly, and dashboard-supporting fields.

## Dashboard Version 1.0.0

Current focus.

Goal:

- Complete the dashboard
- Validate KPIs
- Polish interactions
- Publish the portfolio-ready result

## Future Versions

Infrastructure improvements and new features can be addressed after the dashboard is complete.
