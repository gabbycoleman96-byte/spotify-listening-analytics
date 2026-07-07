# Spotify ETL Pipeline & Analytics Dashboard

A portfolio-quality end-to-end data engineering and analytics project that extracts personal Spotify data using the Spotify Web API, transforms and loads it into MySQL, and visualizes listening trends in Tableau.

---

## Project Overview

This project demonstrates the complete data lifecycle:

Spotify API → Python ETL → MySQL → SQL Transformations → Tableau Dashboard

The goal is to build a reusable ETL framework rather than a collection of standalone scripts. The architecture is modular, scalable, and designed so additional Spotify endpoints can be added with minimal code changes.

---

## Features

### Current

- OAuth authentication with Spotify Web API
- Download entire Liked Songs library
- Download Recently Played history
- Normalize Spotify data for SQL compatibility
- Generic DataFrame loader for MySQL
- Automatic duplicate handling
- Batch inserts for scalability
- Modular ETL architecture
- Raw CSV backups
- SQL-ready data model
- Tableau dashboard integration

---

## Tech Stack

### Languages

- Python
- SQL

### Database

- MySQL

### Python Libraries

- pandas
- spotipy
- mysql-connector-python
- python-dotenv

### Visualization

- Tableau

### Development Tools

- VS Code
- Git
- GitHub

---

# Project Structure

```text
spotify_etl/

│
├── api/
│   ├── authenticate.py
│   └── spotify_client.py
│
├── config/
│   └── settings.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── exports/
│
├── extract/
│   ├── liked_songs.py
│   └── recent_tracks.py
│
├── load/
│   ├── database.py
│   └── loader.py
│
├── sql/
│
├── transform/
│
├── utils/
│   └── helpers.py
│
├── .env
├── main.py
└── requirements.txt
```

---

# ETL Workflow

```
Spotify API
      │
      ▼
Python Extractors
      │
      ▼
Pandas DataFrames
      │
      ▼
Data Cleaning
      │
      ▼
Reusable MySQL Loader
      │
      ▼
MySQL Database
      │
      ▼
SQL Summary Tables
      │
      ▼
Tableau Dashboard
```

---

# Database Design

Current tables include:

- liked_songs
- recent_tracks

Additional analytical summary tables are generated inside the analytics database for Tableau.

---

# Example Pipeline

Running

```bash
python main.py
```

performs the following:

1. Authenticate with Spotify
2. Download liked songs
3. Load liked songs into MySQL
4. Download recently played tracks
5. Load recent tracks into MySQL

---

# Tableau Dashboard

The Tableau dashboard includes interactive visualizations such as:

- Listening history by year
- Listening clock
- Top artists
- Top tracks
- Artist discovery timeline
- Days of My Life visualization
- KPI cards
- Listening trends

*(Dashboard screenshots coming soon.)*

---

# Engineering Concepts Demonstrated

This project intentionally emphasizes software engineering principles in addition to analytics.

Examples include:

- Modular architecture
- Reusable ETL components
- Separation of concerns
- DRY (Don't Repeat Yourself)
- Configuration management
- Batch database loading
- Error handling
- Environment variables
- Duplicate handling
- Incremental ETL design

---

# Future Enhancements

Planned improvements include:

- Incremental liked song synchronization
- Automatic scheduled ETL jobs
- Artist metadata
- Album artwork
- Genre enrichment
- Audio features
- ETL execution logging
- Automated summary table refreshes
- Unit tests
- Docker deployment

---

# About This Project

This project was built as part of my transition into Data Analytics and Data Engineering.

Rather than focusing only on visualizations, I wanted to demonstrate the complete data pipeline from API extraction through database design, transformation, and business intelligence reporting.

The long-term goal is to evolve this project into a reusable ETL framework capable of supporting additional APIs and datasets with minimal changes.