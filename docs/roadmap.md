# Roadmap

## Purpose

This roadmap describes the planned evolution of Spotify Listening Analytics while keeping the current project focused.

The immediate goal is to **finish Dashboard Version 1.0.0**.

Future engineering improvements remain valuable, but they are deliberately separated from the current milestone so the project can actually ship.

---

# Current Milestone: Dashboard Version 1.0.0

## Objective

Complete and publish the Tableau Public dashboard using the current working ETL and warehouse.

### Remaining Priorities

- Finish remaining dashboard pages
- Complete KPI calculations
- Validate KPI results against the warehouse
- Apply anomaly filters where necessary
- Finish tooltips and interactions
- Polish visual consistency
- Complete mobile/Now Playing presentation
- Publish the portfolio-ready Tableau Public dashboard

### Status

**In progress**

---

# Pipeline Version 1.0.0

## Objective

Create a reliable automated ETL foundation.

### Completed

- Historical Spotify Streaming History ingestion
- Raw MySQL table
- Warehouse transformation
- Duplicate handling
- Impossible-play detection
- Metadata enrichment
- Data-quality/anomaly flags
- SQL analytics
- Tableau exports
- Windows Task Scheduler automation
- Execution logging

### Status

**Stable / complete for current dashboard work**

---

# Warehouse Version 1.1

## Current Capabilities

The warehouse now supports:

- Calendar and time dimensions
- Track/artist/album metadata
- Spotify identifiers
- Listening duration
- Album artwork
- Dominant album color
- Navigation/session-related calculations
- Play numbering
- Data-quality flags
- Repeating-playback anomaly flags
- Offline playback timestamp correction

### Status

**Current**

---

# Version 2.0 – Infrastructure and Feature Expansion

Version 2 is where the deferred engineering work belongs.

## Warehouse Improvements

- Incremental warehouse loading
- Avoid rebuilding the entire warehouse on every run
- More efficient loading and indexing
- More formal track/album identity modeling

## Data Quality

- More sophisticated anomaly detection
- Additional validation rules
- Better handling of Spotify export edge cases

## Metadata

Potential additions:

- More complete genre information
- Release metadata
- Additional Spotify track attributes
- External music metadata

## Analytics

Potential additions:

- Listening streaks
- More advanced session analysis
- Artist lifecycle analysis
- Long-term behavioral trends
- More detailed discovery metrics

## Playlist Generation

Potential future feature:

- Generate playlists from the warehouse and metadata
- Create decade-based playlists
- Create vibe/theme playlists
- Evaluate existing playlists for fit
- Potentially automate playlist creation through Spotify

## External Integrations

Potential future sources:

- Last.fm
- MusicBrainz
- Discogs
- Other music metadata services

---

# Long-Term Ideas

These are intentionally unscheduled.

- Recommendation engine
- Machine learning
- Predictive listening models
- Cloud deployment
- Docker
- Web application
- Mobile application
- Power BI version
- Direct database-backed dashboard
- More advanced Spotify automation

---

# Explicitly Deferred

The following are **not current problems to solve**:

- Warehouse rebuild optimization
- Incremental processing
- Major schema refactoring
- New external data sources
- Playlist automation
- Additional enrichment that does not support an existing dashboard requirement

They become relevant after Dashboard Version 1.0.0 is complete.

---

# Guiding Philosophy

```text
Make it work
      ↓
Make the dashboard whole
      ↓
Ship Version 1
      ↓
Then optimize
      ↓
Then add shiny things
```

The project has accumulated enough infrastructure to support the dashboard.

The next achievement is finishing the thing users can actually see.

---

# Next Release Target

After the Tableau Public dashboard is complete, the project can begin a controlled Version 2 planning pass.

No major infrastructure changes should be introduced solely because they are interesting while Dashboard Version 1.0.0 is still unfinished.
