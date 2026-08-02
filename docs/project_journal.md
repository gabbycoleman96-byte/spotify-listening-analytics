# Project Journal

## Purpose

This journal documents the evolution of the Spotify Listening Analytics project from its original concept to Version 1.0.0.

Unlike the changelog, which records *what* changed, this journal explains *why* the project evolved the way it did, the challenges encountered, and the lessons learned throughout development.

---

# The Original Idea

This project began with a simple goal:

> Create a Tableau dashboard that visualized my personal Spotify listening history.

Initially, I expected the work to revolve around SQL queries and dashboard design. I planned to import Spotify's Extended Streaming History into MySQL, create a handful of summary tables, and connect Tableau to the results.

Very quickly, it became clear that the data pipeline itself would become the most interesting part of the project.

---

# Phase 1 – Exploring the Data

The first stage focused on understanding Spotify's data.

Tasks completed:

- Imported historical streaming history
- Cleaned raw JSON data
- Standardized timestamps
- Removed duplicates
- Created the first MySQL tables
- Built exploratory SQL queries

This phase answered an important question:

> *What information does Spotify actually provide, and how can it be modeled?*

---

# Phase 2 – The Summary Table Approach

The original architecture relied on manually maintained summary tables.

Examples included:

- yearly_summary
- hourly_summary
- artist_summary
- artist_summary_by_year
- track_summary

At first this seemed reasonable.

However, each new dashboard idea required creating another SQL table or modifying an existing one.

Business logic quickly became scattered across the project.

Although functional, the design did not scale well.

---

# Phase 3 – Rethinking the Architecture

One of the biggest turning points came when I realized that I wasn't building dashboards.

I was building a data platform.

Instead of creating tables specifically for Tableau, I redesigned the project around a single warehouse.

The project shifted from:

```text
Raw Data
↓

Summary Tables

↓

Dashboard
```

to:

```text
Raw Data

↓

Warehouse

↓

Analytics

↓

Dashboard
```

This became the defining architectural decision of Version 1.

---

# Phase 4 – Building the ETL Pipeline

With the warehouse established, the next goal became automation.

The pipeline was redesigned to:

1. Download newly liked songs.
2. Download recently played tracks.
3. Refresh the API snapshot.
4. Append new listening events.
5. Rebuild analytics tables.
6. Export Tableau-ready CSV files.

Windows Task Scheduler was used to automate execution every thirty minutes.

The result was a continuously growing warehouse requiring minimal manual maintenance.

---

# Phase 5 – Historical Imports

Spotify's Extended Streaming History export became the foundation of the warehouse.

Instead of importing data manually each time, a dedicated importer was developed to:

- Read multiple JSON files
- Standardize fields
- Create calendar dimensions
- Enrich listening events
- Load the warehouse

This separated one-time historical imports from recurring API updates.

---

# Phase 6 – Simplifying the Project

As the project matured, several architectural decisions were revisited.

Examples included:

- Renaming `dashboard_data` to `spotify_listening_warehouse`
- Renaming `recent_tracks_snapshot` to `recent_50_tracks_snapshot`
- Removing the unnecessary `listening_history_api` table
- Retiring legacy summary tables
- Reorganizing the repository
- Standardizing naming conventions

Each change reduced complexity and made the project easier to understand.

One lesson became increasingly clear:

> Good software often becomes simpler over time, not more complicated.

---

# Challenges

Several technical challenges emerged throughout development.

## Duplicate Detection

Historical exports and live API data occasionally overlapped.

The warehouse was redesigned to prevent duplicate listening events while preserving legitimate repeat plays.

---

## Timestamp Normalization

Spotify exports and Spotify API responses used different timestamp formats.

A consistent datetime strategy was implemented to allow both sources to coexist within the same warehouse.

---

## Scope Management

One of the biggest non-technical challenges was resisting the temptation to continuously add new features.

Ideas such as:

- Genre enrichment
- Album artwork
- Recommendation systems
- Machine learning
- Cloud deployment

were intentionally postponed.

The decision was made to complete a polished Version 1 before expanding the project further.

---

# Lessons Learned

## Architecture Matters

Investing time in the overall architecture reduced future development effort.

Well-designed foundations made later features significantly easier to implement.

---

## Naming Matters

Clear, descriptive names improved readability throughout the project.

Renaming tables and modules often eliminated confusion without changing functionality.

---

## Automation Saves Time

Automating repetitive tasks quickly became one of the most rewarding aspects of the project.

Rather than manually rebuilding reports, the project evolved into a pipeline that maintains itself.

---

## Build for Future You

Several refactors were motivated by a simple question:

> "Will I understand this six months from now?"

Design decisions increasingly prioritized maintainability over short-term convenience.

---

# Version 1.0 Milestone

Version 1 represents the completion of the data engineering phase of the project.

Major accomplishments include:

- Automated Spotify API integration
- Historical streaming history importer
- Unified MySQL warehouse
- Automated analytics generation
- Scheduled ETL pipeline
- Tableau-ready exports
- Comprehensive project documentation

With the pipeline complete, future development shifts toward visualization, storytelling, and dashboard design.

---

# Looking Ahead

Version 1.1 will focus on refining the existing platform through performance improvements and data enrichment.

Version 2 will introduce entirely new capabilities while preserving the warehouse-first architecture established during Version 1.

The project began as a dashboard.

It evolved into an automated analytics platform.

That evolution became the most valuable outcome of the project.