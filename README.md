# Spotify Listening Analytics

> An end-to-end data engineering and analytics project that automatically collects, stores, transforms, and visualizes Spotify listening history using Python, MySQL, and Tableau.

![Version](https://img.shields.io/badge/version-1.0.0-success)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.x-orange)
![Tableau](https://img.shields.io/badge/Tableau-Public-blue)

---

## Overview

Spotify Listening Analytics is a portfolio project that demonstrates the complete analytics lifecycle, from raw API data to interactive business intelligence dashboards.

Rather than relying on static datasets, this project continuously builds a personal Spotify data warehouse by combining:

- Historical Spotify Extended Streaming History exports
- Live Spotify Web API data
- Automated ETL processing
- SQL-based analytics
- Tableau Public dashboards

The result is a fully automated reporting pipeline that requires little manual intervention once configured.

---

## Project Goals

This project was designed to demonstrate practical data engineering and analytics skills commonly used in production environments.

Specifically, it showcases:

- Designing and maintaining a relational data warehouse
- Building modular ETL pipelines in Python
- Working with REST APIs
- Automating recurring workflows
- Creating reusable SQL analytics tables
- Building interactive Tableau dashboards
- Writing maintainable, documented code

---

# Architecture

```text
                    Spotify Web API
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
Liked Songs API                  Recently Played API
         │                                   │
         └──────────────┬────────────────────┘
                        │
              Python ETL Pipeline
                        │
        Historical Spotify Export Import
                        │
                        ▼
        spotify_listening_warehouse (MySQL)
                        │
          ┌─────────────┼──────────────┐
          │             │              │
          ▼             ▼              ▼
 Artist Analytics  Listening Analytics  Library Analytics
          │             │              │
          └─────────────┼──────────────┘
                        │
                 CSV Export Pipeline
                        │
                        ▼
                 Tableau Public
```

---

# Repository Structure

```text
spotify_etl/

├── api/
├── config/
├── export/
├── extract/
├── load/
├── sql/
│   ├── schema/
│   ├── analytics/
│   └── archive/
├── transform/
├── utils/
├── testers/
│
├── main.py
├── requirements.txt
├── README.md
```

---

# ETL Pipeline

The pipeline executes automatically every 30 minutes using Windows Task Scheduler.

Each run performs the following steps:

1. Download newly liked songs from Spotify.
2. Download the latest 50 recently played tracks.
3. Refresh the snapshot table.
4. Append new listening events to the warehouse.
5. Rebuild analytics tables.
6. Export Tableau-ready CSV files.
7. Log execution statistics.

---

# Database Design

## Core Tables

| Table | Purpose |
|--------|---------|
| spotify_listening_warehouse | Master fact table containing every listening event |
| liked_songs | Current Spotify library |
| recent_50_tracks_snapshot | Mirrors Spotify's Recently Played endpoint |
| etl_log | Pipeline execution history |

## Analytics Tables

| Table | Purpose |
|--------|---------|
| artist_discovery | Artist discovery metrics |
| artist_loyalty | Long-term artist engagement |
| forgotten_favorites | Previously loved artists no longer played |
| listening_session_summary | Listening session analysis |
| repeat_behavior | Repeat listening patterns |

---

# Technology Stack

### Languages

- Python
- SQL

### Database

- MySQL 8

### Libraries

- pandas
- mysql-connector-python
- requests
- python-dotenv

### Visualization

- Tableau Public

### Automation

- Windows Task Scheduler

---

# Features

## Automated ETL

- Incremental Spotify API ingestion
- Historical streaming history import
- Duplicate prevention
- Automatic warehouse updates

## Analytics

- Artist discovery tracking
- Loyalty metrics
- Forgotten favorites
- Listening session analysis
- Repeat behavior

## Dashboard

- Interactive Tableau dashboards
- Dynamic filtering
- Automated data refresh
- Mobile-inspired dashboard design

---

# Future Enhancements

Version 1.1

- Genre enrichment
- Album artwork
- Dominant album colors
- SQLAlchemy migration
- Improved retry handling

Version 2.0

- Recommendation engine
- Additional behavioral analytics
- Cloud deployment
- Direct database dashboards

---

# Screenshots

> Screenshots will be added after Dashboard Version 1.0 is complete.

---

# Author

**Gabby Coleman**

Career Coach transitioning into Data Analytics and Data Engineering.

---

# License

This project is provided for educational and portfolio purposes.