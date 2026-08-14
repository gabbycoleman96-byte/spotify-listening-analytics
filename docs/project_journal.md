# Project Journal

## Purpose

This journal records the evolution of Spotify Listening Analytics, including the decisions, problems, discoveries, and lessons that shaped the current project.

The project began as a Tableau dashboard and gradually became a full personal analytics pipeline.

---

# Phase 1 – The Dashboard Idea

The original goal was straightforward:

> Build a Tableau dashboard from personal Spotify listening history.

The initial plan centered on importing Spotify Extended Streaming History into MySQL, creating summary tables, and connecting Tableau.

That plan quickly grew into something much larger.

---

# Phase 2 – The Summary Table Era

Early versions used separate summary tables for different dashboard needs.

Examples included yearly, hourly, artist, track, and other purpose-built summaries.

This worked, but every new dashboard idea created another piece of SQL logic.

The project was becoming a collection of answers instead of a reusable data source.

---

# Phase 3 – The Warehouse Pivot

The major architectural turning point was the decision to build a central listening warehouse.

The structure became:

```text
Raw Spotify History
        ↓
Warehouse
        ↓
Analytics
        ↓
Tableau
```

This became the foundation of the current project.

The primary analytical table evolved into:

```text
listening_history_warehouse
```

while the original Spotify data was preserved separately in:

```text
listening_history_raw
```

---

# Phase 4 – Building the ETL

The project grew into a modular Python ETL pipeline handling:

- Historical Spotify data
- Transformation
- Cleaning
- Metadata enrichment
- MySQL loading
- SQL analytics
- Tableau exports
- Execution logging
- Automated scheduling

Windows Task Scheduler was used to make the process recurring.

---

# Phase 5 – Historical Data Validation

The latest combined Spotify export contains:

```text
824,845 raw records
```

with coverage from:

```text
2014-07-04 03:56:48
through
2026-08-07 23:59:41
```

After cleaning and transformation, the current warehouse contains approximately:

```text
804,193 retained records
```

The difference comes from duplicate removal, impossible-play removal, records lacking required metadata, and other transformation rules.

---

# Phase 6 – The July 5, 2022 Anomaly

A major data-quality investigation began while building a Tableau KPI for:

> Most plays of a song in a single day.

July 5, 2022 produced an implausibly high number of plays for five tracks:

- Could Have Been Me
- Everybody Talks
- Champion
- Young Volcanoes
- Body Talks (feat. Kesha)

The raw export revealed a repeating playback sequence occurring throughout the day.

The investigation confirmed that these were not ordinary independent listening events. The pattern was treated as a repeating playback-loop anomaly rather than blindly deleting the raw records.

The warehouse now flags these records using:

```text
is_anomaly = 1
anomaly_type = repeating_playback_loop
```

This allows dashboard metrics to exclude them where necessary while retaining the historical evidence.

---

# Phase 7 – Offline Playback Investigation

Another issue appeared when comparing historical listening patterns.

Spotify's raw `ts` is not always the best representation of when an offline track was actually played.

The raw export includes:

```text
offline
offline_timestamp
```

The transformation was updated so that a valid offline timestamp can replace `ts` when determining the canonical `played_at`.

A second complication emerged during testing: Spotify's export contains both seconds-scale and milliseconds-scale Unix timestamps in `offline_timestamp`.

The conversion was therefore changed to determine the timestamp unit from the value's magnitude.

This prevents offline synchronization behavior from producing wildly incorrect calendar dates.

---

# Phase 8 – Understanding the Difference From stats.fm

The project was compared against stats.fm to understand why the dashboard's stream totals differ from another Spotify listening-history service.

Several differences are expected because services may apply different data-cleaning and counting rules.

One important discovery was that:

> Average streams per listening day is not the same metric as average streams per calendar day.

The project's current calculation is based on days represented in the listening data, while another service may divide by the full calendar period.

This distinction is now understood and does not by itself indicate a warehouse problem.

The comparison also reinforced the need to treat Spotify listening-history data as an imperfect event log rather than an unquestionable record of human intent.

---

# Phase 9 – The Stability Decision

At this point the project had reached an important threshold.

The ETL worked.

The warehouse worked.

The dashboard was working.

Further architectural improvements were beginning to compete with the actual goal: finishing the dashboard.

The decision was made to stop expanding the infrastructure unless a dashboard requirement genuinely requires it.

In particular, the warehouse will continue rebuilding for now.

Incremental loading can be revisited in a future version.

This is a deliberate scope boundary, not an unfinished emergency.

---

# Current Project State

The project is now in:

## Dashboard Version 1.0.0 Completion

The immediate work is:

- Finish remaining Tableau dashboards
- Finish and validate KPIs
- Resolve any data-quality filters required by individual visuals
- Polish interactions and tooltips
- Complete the Tableau Public portfolio presentation

The ETL is considered stable enough to support this work.

---

# Lessons Learned

## The data is weirder than the dashboard

Spotify's export contains edge cases that are invisible until you ask very specific questions of it.

A KPI that sounds simple can uncover a data-engineering investigation.

---

## Preserve the raw data

Having the raw table made it possible to investigate suspicious records without losing the original evidence.

---

## Flag questionable data when certainty is impossible

The July 5 loop demonstrated why anomaly flags are useful.

Not every strange record should be deleted simply because it looks strange.

---

## Don't optimize a working system during the finish line

The current warehouse rebuild is not ideal from a performance perspective.

It is, however, working.

The project now prioritizes completing the dashboard over making the pipeline theoretically perfect.

---

# Current Milestone

The project has moved through:

```text
Dashboard idea
      ↓
Exploratory SQL
      ↓
Summary tables
      ↓
Warehouse redesign
      ↓
Automated ETL
      ↓
Data-quality investigation
      ↓
Dashboard development
      ↓
★ CURRENT: Dashboard completion
```

The next milestone is not another architecture rewrite.

It is shipping the dashboard.
