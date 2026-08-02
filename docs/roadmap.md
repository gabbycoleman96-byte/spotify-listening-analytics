# Roadmap

## Purpose

This roadmap outlines the planned evolution of Spotify Listening Analytics beyond Version 1.0.0.

The project follows semantic versioning, where each major release focuses on a specific objective while avoiding unnecessary scope expansion.

The goal is to continuously improve the project without compromising stability or maintainability.

---

# Version 1.0.0 (Current)

## Objective

Build a complete, automated Spotify analytics platform.

### Completed

✔ Historical Spotify Streaming History importer

✔ Spotify Web API integration

✔ Automated ETL pipeline

✔ MySQL listening warehouse

✔ Analytics SQL layer

✔ Automated CSV exports

✔ Windows Task Scheduler automation

✔ Project documentation

✔ Tableau dashboard framework

Status

**Complete**

---

# Version 1.1

## Objective

Refine the existing platform without changing its overall architecture.

### Planned Features

### Data Enrichment

- Retrieve primary genre for every track
- Retrieve secondary genre
- Store album artwork URLs
- Extract dominant album artwork colors
- Store track popularity
- Store release year

---

### Pipeline Improvements

- Incremental historical import support
- SQLAlchemy database integration
- Improved validation
- Retry logic for Spotify API failures
- Better error reporting

---

### Performance

- Additional indexing
- Faster warehouse loading
- Export optimization

---

### Documentation

- Architecture diagrams
- Dashboard screenshots
- ETL sequence diagrams

---

# Version 2.0

## Objective

Expand analytical capabilities.

Potential features include:

### Behavioral Analytics

- Listening streaks
- Mood analysis
- Listening habit changes
- Artist lifecycle analysis

---

### Recommendation Engine

Explore recommendation systems based on:

- Listening history
- Artist similarity
- Genre preferences
- Seasonal trends

---

### Dashboard Expansion

Potential dashboard pages

- Genres
- Albums
- Listening Sessions
- Discovery Timeline
- Listening Calendar
- Annual Spotify Wrapped

---

### Additional Integrations

Potential future data sources

- Last.fm
- MusicBrainz
- Discogs

---

# Long-Term Ideas

Ideas below are intentionally not scheduled.

These concepts remain outside the scope of Version 1.

Examples include:

- Machine learning
- Predictive listening models
- Cloud deployment
- Docker
- Web application
- Mobile dashboard
- Direct Tableau database connection
- Power BI version
- Personal recommendation engine

---

# Guiding Philosophy

One lesson became clear during development:

> A project is never truly finished, but every version should be.

Future ideas are intentionally separated into later releases.

This keeps Version 1 stable while providing a clear direction for future development.

---

# Current Focus

The immediate priority following Pipeline Version 1.0.0 is completing Dashboard Version 1.0.0 for Tableau Public.

Once the dashboard is published, development will shift toward Version 1.1 improvements.