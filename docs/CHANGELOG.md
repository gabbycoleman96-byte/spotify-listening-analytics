# Changelog

All notable changes to this project are documented in this file.

This project follows Semantic Versioning.

---

# [1.0.0] - Initial Release

## Overview

Version 1.0.0 represents the completion of the project's data engineering phase.

The project evolved from a manually maintained SQL dashboard into a fully automated analytics platform built around a centralized data warehouse.

---

## Added

### Data Collection

- Spotify Web API integration
- Historical Streaming History importer
- Incremental liked song downloads
- Incremental recently played downloads

---

### ETL Pipeline

- Automated Python ETL pipeline
- Warehouse loader
- Data transformation layer
- Duplicate protection
- Execution logging

---

### Database

- MySQL warehouse
- Analytics tables
- Snapshot staging table
- ETL logging table

---

### Analytics

Added automated SQL generation for:

- Artist Discovery
- Artist Loyalty
- Forgotten Favorites
- Listening Session Summary
- Repeat Behavior

---

### Export

- Automated Tableau CSV exports

---

### Documentation

Added

- README
- Architecture documentation
- Design Decisions
- Data Dictionary
- Project Journal
- Roadmap
- Changelog

---

## Changed

### Architecture

Migrated from manually maintained summary tables to a warehouse-first architecture.

---

Renamed

```text
dashboard_data
```

↓

```text
spotify_listening_warehouse
```

---

Renamed

```text
recent_tracks_snapshot
```

↓

```text
recent_50_tracks_snapshot
```

---

Removed the intermediate

```text
listening_history_api
```

table.

---

Reorganized repository structure.

---

Converted project paths to relative paths for portability.

---

## Fixed

Resolved duplicate warehouse imports.

Standardized timestamp parsing across historical exports and live Spotify API data.

Improved incremental loading.

Simplified ETL execution.

Improved naming consistency throughout the project.

---

## Removed

Retired legacy summary tables.

Removed obsolete migration scripts.

Eliminated duplicate ETL logic.

---

# Future

See `roadmap.md` for planned enhancements.