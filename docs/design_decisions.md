# Design Decisions

## Purpose

This document explains the architectural and technical decisions made throughout the development of Spotify Listening Analytics.

Rather than simply documenting the implementation, this document focuses on the reasoning behind major design choices, including alternatives that were considered and why the final approach was selected.

---

# Guiding Principles

Several principles guided every major decision throughout the project.

- Simplicity over unnecessary complexity.
- Automation over manual processes.
- One source of truth.
- Reusable components.
- Maintainability over premature optimization.
- Design for future expansion.

These principles often resulted in choosing a solution that required more work initially but significantly reduced long-term maintenance.

---

# Why Build a Data Warehouse?

## Decision

Create a centralized warehouse containing every listening event instead of generating multiple independent summary datasets.

## Rationale

Early versions of the project relied on manually maintained summary tables. While this approach worked initially, every new visualization required additional SQL queries and duplicated business logic.

A warehouse-first architecture provides a single source of truth that can support unlimited downstream analytics.

Benefits include:

- Consistent calculations
- Easier maintenance
- Simpler dashboard development
- Better scalability
- Reduced duplication

---

# Why MySQL?

Several storage options were considered.

## SQLite

Advantages

- Extremely simple setup
- Lightweight
- Portable

Disadvantages

- Less representative of enterprise environments
- Limited scalability
- Fewer optimization opportunities

## PostgreSQL

Advantages

- Excellent analytical capabilities
- Strong SQL compliance

Disadvantages

- Additional learning curve
- More administrative overhead for this project

## MySQL (Selected)

Reasons

- Widely used in industry
- Excellent documentation
- Reliable Python support
- Strong SQL feature set
- Appropriate complexity for the project

---

# Why Python?

Python serves as the orchestration layer for the ETL pipeline.

Responsibilities include:

- API communication
- JSON processing
- Data transformation
- Database loading
- Export automation
- Scheduling integration

Separating orchestration from SQL keeps each language focused on its strengths.

---

# Why SQL Analytics Instead of Tableau Calculations?

Business logic belongs as close to the data as possible.

Complex calculations are performed once inside MySQL rather than repeatedly inside Tableau.

Advantages

- Faster dashboards
- Reusable analytics
- Easier debugging
- Centralized business logic
- Consistent calculations

The Tableau dashboards focus primarily on visualization rather than data processing.

---

# Why Use a Snapshot Table?

The project maintains a dedicated table named:

```text
recent_50_tracks_snapshot
```

This table mirrors Spotify's "Recently Played" endpoint.

Reasons

- Simplifies debugging
- Makes API responses inspectable
- Separates raw API data from the warehouse
- Provides an intermediate validation layer

Only validated data is appended into the warehouse.

---

# Why Remove listening_history_api?

Earlier versions of the project contained an intermediate table that stored API listening history before loading the warehouse.

As the architecture evolved, this table became unnecessary.

Original flow

```text
Spotify API

↓

Snapshot

↓

Listening History API

↓

Warehouse
```

Current flow

```text
Spotify API

↓

Snapshot

↓

Warehouse
```

Removing the intermediate table reduced:

- complexity
- maintenance
- duplicated storage
- unnecessary transformations

without losing functionality.

---

# Why a Warehouse Instead of Dashboard Data?

Earlier versions referred to the primary table as:

```text
dashboard_data
```

This name implied the table existed only to support Tableau.

The project has evolved beyond that.

The table now supports:

- SQL analytics
- Tableau
- Python analysis
- Future Power BI dashboards
- Future machine learning experiments

The new name

```text
spotify_listening_warehouse
```

better reflects its role as the project's central repository.

---

# Why Relative Paths?

Early development used absolute file paths.

Example

```text
C:\Users\Gabby\Downloads\spotify_etl
```

This prevented the project from moving between computers.

The project now resolves paths relative to the project root.

Advantages

- Portable
- GitHub friendly
- Google Drive compatible
- Cross-machine development

---

# Why Export CSV Files?

Several options were considered.

## Direct MySQL Connection

Advantages

- Live database connection
- No intermediate files

Disadvantages

- More difficult for public portfolio sharing
- Additional setup required

## CSV Export (Selected)

Advantages

- Simple
- Portable
- Tableau Public compatible
- Easy to version
- Easy to inspect

This approach prioritizes accessibility and reproducibility for portfolio reviewers.

---

# Why a Modular ETL?

The ETL is separated into independent stages.

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

Benefits

- Easier testing
- Clear responsibilities
- Better readability
- Simpler maintenance
- Independent upgrades

---

# Versioning Philosophy

The project intentionally distinguishes between feature development and refinement.

## Version 1.0

Goal

Create a reliable, maintainable, automated analytics platform.

Focus

- Correctness
- Documentation
- Automation
- Architecture

## Version 1.1

Focus

- Performance improvements
- Additional enrichment
- Retry logic
- SQLAlchemy
- Incremental historical imports

## Version 2

Focus

New functionality rather than infrastructure improvements.

Examples

- Recommendation engine
- Machine learning
- Behavioral prediction
- Additional dashboards

---

# Lessons Learned

Several important software engineering lessons emerged during development.

## Architecture Matters

Investing time in project organization significantly reduced later complexity.

## Naming Matters

Clear, descriptive names reduced confusion and improved maintainability.

## Build Once, Reuse Everywhere

Centralizing business logic inside the warehouse eliminated duplicated calculations.

## Finish Before Expanding

Many interesting feature ideas emerged during development.

Rather than continually expanding scope, Version 1 intentionally prioritizes a complete, polished product before adding additional capabilities.

This decision keeps the project focused while providing a stable foundation for future releases.