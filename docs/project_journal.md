# Project Journal

## Purpose

This journal records the evolution of Spotify Listening Analytics, including the decisions, problems, discoveries, and lessons that shaped the project.

What began as a Tableau dashboard built from personal Spotify listening history has grown into a data-engineering pipeline with a MySQL warehouse, automated processing, data-quality rules, catalog identity resolution, external music metadata, SQL analytics, and Tableau Public dashboards.

This document records both the technical milestones and the reasoning behind them.

---

# Phase 1: The Dashboard Idea

The original goal was straightforward:

> Build a Tableau dashboard from personal Spotify listening history.

The initial plan centered on importing Spotify Extended Streaming History into MySQL, creating summary tables, and connecting Tableau.

The project quickly grew beyond that original scope as new questions about listening habits required more flexible data and more sophisticated analytical logic.

---

# Phase 2: The Summary Table Era

Early versions used separate summary tables for different dashboard requirements.

Examples included yearly, hourly, artist, track, and other purpose-built summaries.

This worked for individual visualizations, but every new dashboard idea created another piece of SQL logic to maintain.

The project was becoming a collection of answers rather than a reusable analytical system.

That limitation led to the next major architectural change.

---

# Phase 3: The Warehouse Pivot

The decision was made to build a central listening-history warehouse.

The architecture became:

```text
Raw Spotify History
        ↓
Transformation and Cleaning
        ↓
Listening-History Warehouse
        ↓
SQL Analytics and Exports
        ↓
Tableau Public
```

The primary analytical table became:

```text
listening_history_warehouse
```

The original imported data was preserved separately in:

```text
listening_history_raw
```

This separation made it possible to revise cleaning and transformation rules without modifying the source history.

The warehouse became the foundation for new dashboard views and analytical questions.

---

# Phase 4: Building the Automated ETL

The project developed into a modular Python ETL pipeline.

Its responsibilities expanded to include:

- Historical listening-history processing.
- Data cleaning and transformation.
- MySQL loading.
- Spotify catalog metadata.
- SQL analytics and summary-table rebuilding.
- Tableau-ready exports.
- Pipeline execution logging.
- Automated scheduling through Windows Task Scheduler.

The project was no longer simply a dashboard connected to a database. It had become a repeatable data-processing workflow.

The pipeline was organized so that extraction, transformation, loading, analytics, and export could be maintained as distinct responsibilities.

---

# Phase 5: Historical Data Validation

A combined Spotify export was assembled to provide a continuous historical source for the project.

The validation snapshot recorded during this phase contained:

```text
824,845 raw records
```

with coverage from:

```text
2014-07-04 03:56:48
through
2026-08-07 23:59:41
```

The warehouse at that point contained approximately:

```text
804,193 retained records
```

The difference reflected cleaning and transformation rules, including duplicate removal, impossible-play removal, missing required information, and other processing decisions.

These figures document a historical validation snapshot, not a guaranteed current database count. Later exports and transformation changes can alter the totals.

This phase established an important principle: warehouse counts must be interpreted in the context of the rules used to produce them.

---

# Phase 6: The July 5, 2022 Playback Anomaly

A major data-quality investigation began while developing a Tableau KPI for:

> Most plays of a song in a single day.

July 5, 2022 produced an implausibly high number of plays for five tracks:

- Could Have Been Me
- Everybody Talks
- Champion
- Young Volcanoes
- Body Talks (feat. Kesha)

Inspection of the raw export revealed a repeating playback sequence throughout the day.

The pattern was not representative of ordinary independent listening events and would distort a metric intended to describe listening behavior.

Rather than blindly deleting the raw records, the project introduced anomaly identification in the warehouse.

The relevant fields are:

```text
is_anomaly
anomaly_type
```

The repeating playback pattern is identified using:

```text
is_anomaly = 1
anomaly_type = repeating_playback_loop
```

This allows analytical queries and Tableau dashboards to exclude the affected events where appropriate while retaining the original history for investigation.

### Lesson learned

An unusual record is not automatically an invalid record. Separating definitive cleaning rules from anomaly flags makes the analytical results easier to explain and audit.

---

# Phase 7: Offline Playback Investigation

Another investigation began when examining historical listening patterns.

Spotify's raw `ts` field does not always represent the time an offline track was actually played. It can reflect when the offline event was synchronized.

The export also contains:

```text
offline
offline_timestamp
```

The transformation was updated so that a valid offline timestamp can replace the raw timestamp when determining the canonical `played_at` value.

A second complication emerged: the export contains `offline_timestamp` values at both seconds-scale and milliseconds-scale Unix timestamp magnitudes.

The transformation therefore determines the timestamp scale before converting the value.

Calendar and time-of-day dimensions are then derived from `played_at`.

### Lesson learned

A timestamp can be syntactically valid but analytically misleading. Correct interpretation of the source fields matters just as much as converting them into the right data type.

---

# Phase 8: Understanding Differences From stats.fm

The project was compared with stats.fm to investigate differences in reported listening totals.

The comparison highlighted that services can apply different counting and cleaning rules to the same underlying listening history.

One important distinction was:

> Average streams per listening day is not the same metric as average streams per calendar day.

A calculation based on days represented in the listening data can produce a different result from one that divides by every calendar day in a period.

The comparison also reinforced the need to document metric definitions instead of assuming that two services use identical calculations.

### Lesson learned

A difference between two dashboards does not automatically mean that one is wrong. Before changing the warehouse, first establish whether the metrics actually measure the same thing.

---

# Phase 9: The Stability Decision

As the ETL and warehouse matured, additional architectural improvements began competing with the original goal of completing the Tableau dashboard.

The project had reached a point where the working pipeline could support the remaining dashboard development.

The decision was made to prioritize stability and completion rather than continuously redesigning the infrastructure.

The warehouse would continue rebuilding during pipeline runs for the current version. Incremental loading and broader performance optimization would be deferred.

This established an explicit scope boundary for Dashboard Version 1.0.0.

### Lesson learned

A technically interesting improvement is not automatically the next most valuable task. Finishing a working product is itself an engineering decision.

---

# Phase 10: Song Identity Resolution

As the project expanded beyond basic listening totals, it became increasingly important to distinguish a Spotify catalog entry from the underlying song identity.

A song may appear under multiple Spotify track IDs because of remasters, reissues, alternate releases, regional catalog differences, and other variations.

Treating every track ID as a completely separate song can fragment listening counts and library analysis.

The project introduced a dedicated identity-resolution layer using:

```text
song_identity_map
canonical_song_uris
```

The identity mapping records canonical IDs and resolution details, allowing decisions to be inspected rather than buried in individual SQL queries.

The process also supports review of ambiguous cases instead of assuming that similar titles always represent the same recording.

### Why this matters

Canonical identity is a foundation for more advanced analysis, including:

- Consolidating listening history across selected track variants.
- Comparing liked status with canonical song identity.
- Reducing duplicate-looking entries in library analysis.
- Selecting a consistent representative track for later features.

### Lesson learned

Matching text is not the same as matching identity. A reliable system needs explicit rules for when records can be combined and when they should remain separate.

---

# Phase 11: MusicBrainz Enrichment

The project added a dedicated MusicBrainz enrichment process to supplement Spotify's catalog metadata.

The goal was to obtain recording-oriented metadata that could support stronger identity decisions and release-date analysis.

The implementation was kept separate from the core listening-history transformation and stores results in:

```text
musicbrainz_track_metadata
```

The database also includes a `musicbrainz_artist_metadata` table for the broader metadata model, although the current integrated MusicBrainz enrichment job focuses on tracks.

The track enrichment process considers available matching evidence, including artist credits, track duration, and duplicate or ambiguous candidates.

It stores match outcomes and supporting information rather than treating every lookup as a successful match.

### Release-date investigation

One important use case was determining the earliest known release date for a recording or track.

This information can help select a canonical version when several Spotify entries appear to represent the same song.

The enrichment process records release-date precision as well as the date itself, because a year-only result is less specific than a complete date.

The investigation also exposed cases where a match could be found but a usable release date could not.

Those cases were retained as known limitations rather than treated as proof that the recording had no release history.

### Initial enrichment results

An overnight MusicBrainz run produced the following snapshot:

| Result | Count |
|---|---:|
| Matched | 15,420 |
| Not found | 5,328 |
| Ambiguous | 1,851 |

Seven records initially reported errors. Follow-up investigation identified malformed or hyphenated ISRC values among the issues, and normalization allowed six of those records to be retried successfully.

The results demonstrate why normalization, explicit lookup statuses, and targeted retries matter when integrating external catalog data.

These counts document that particular run and should not be interpreted as current totals after subsequent retries or enrichment changes.

### Lesson learned

External catalog matching is a data-quality process, not merely an API request. A useful enrichment layer needs to preserve uncertainty and explain why a candidate was accepted, rejected, or left unresolved.

---

# Phase 12: Last.fm Enrichment

After establishing the MusicBrainz layer, the project added Last.fm as a second external music-data source.

The purpose was to enrich the catalog with information that Spotify's own metadata does not fully provide.

The Last.fm layer includes track and artist metadata tables:

```text
lastfm_track_metadata
lastfm_artist_metadata
```

It also includes separate tag tables:

```text
external_track_tags
external_artist_tags
```

These tables retain source attribution and support multiple tags for a track or artist.

The enrichment data can include information such as listener counts, play counts, descriptive summaries, and community-associated tags, depending on what the API returns.

### Initial testing

The initial limited test runs successfully matched all ten tested tracks and all ten tested artists. Tag results varied by item, including records with no tags.

That variation was important: a successful metadata lookup does not guarantee that every optional field will be populated.

### Caching and API handling

The Last.fm integration uses the database as a persistent cache and observes a request interval to avoid sending requests too rapidly.

Lookup statuses and messages are retained so the process can distinguish successful matches, unsuccessful lookups, and technical errors.

The external enrichment scripts are separate from the core warehouse transformation, and their integration allows the main pipeline to report a warning when an enrichment command fails rather than automatically treating the entire run as a core ETL failure.

### Lesson learned

Different external sources contribute different kinds of evidence. Keeping their data separate makes it easier to combine them thoughtfully without pretending that every source uses the same definitions or matching standards.

---

# Phase 13: Integrating External Enrichment Into the Pipeline

With both MusicBrainz and Last.fm enrichment implemented, the project added an external music metadata stage to the main ETL workflow.

The stage runs the separate enrichment processes for:

1. MusicBrainz track metadata.
2. Last.fm track metadata and tags.
3. Last.fm artist metadata and tags.

This allows the external metadata caches to be maintained through the recurring pipeline while preserving the ability to run the enrichment scripts independently.

The integration also distinguishes between a core pipeline failure and an enrichment warning.

For example, an external API problem should not automatically prevent the pipeline from refreshing the core listening-history warehouse and Tableau exports.

However, a warning-free script exit does not prove that every individual API lookup succeeded. Individual lookup outcomes remain available in the enrichment tables.

### Design principle

External metadata should expand the analytical capabilities of the project without becoming an unnecessary single point of failure for its core listening-history workflow.

---

# Current Project State

## Primary milestone: Dashboard Version 1.0.0 completion

The current priority is completing and validating the Tableau Public dashboards.

The project now includes a broader data foundation than the original dashboard required:

- Raw historical listening data.
- A transformed MySQL listening-history warehouse.
- Data-quality and anomaly flags.
- Offline timestamp correction.
- Spotify catalog metadata.
- Canonical song identity mapping.
- MusicBrainz track enrichment.
- Last.fm track and artist enrichment.
- Source-attributed external tags.
- SQL analytics and Tableau-ready exports.
- Automated pipeline execution and logging.

The external metadata layer is available to support current or future analytical requirements. Not every available enrichment field is necessarily used by the current dashboards.

The next development work should be driven by the remaining dashboard requirements rather than by adding infrastructure simply because it is possible.

---

# Lessons Learned

## 1. The data is weirder than the dashboard

A KPI that sounds simple can uncover a complicated data-engineering investigation.

The playback anomaly and offline timestamp issues are examples of problems that were not obvious until the data was examined through specific analytical questions.

## 2. Preserve the raw data

The raw table made it possible to investigate suspicious records and revise transformation rules without losing the original evidence.

## 3. Define metrics before comparing them

Two services can report different values because their definitions, denominators, and filtering rules differ.

Metric definitions are part of the data model, not just presentation details.

## 4. Separate certainty from suspicion

Definitive cleaning rules and anomaly flags solve different problems. The project benefits from preserving questionable records when the evidence does not justify deleting them.

## 5. External metadata needs provenance

An API result should not be treated as unquestionable truth. Source attribution, match scores, lookup statuses, and release-date precision help preserve context and uncertainty.

## 6. Matching is not the same as identity

Track titles, artist names, identifiers, durations, and release information provide evidence, but no single field resolves every catalog variation.

Canonical identity requires explicit decisions and a way to review ambiguous cases.

## 7. Cache external data

Persistent caches reduce unnecessary requests and provide a record of lookup outcomes. They also make external enrichment easier to troubleshoot independently of the core ETL.

## 8. A warning is not the same as a failed warehouse refresh

The pipeline has different responsibilities. A failure in an optional enrichment process should be visible without automatically preventing the core analytical datasets from being refreshed.

## 9. Don't optimize a working system at the finish line

The warehouse rebuild is a known trade-off. Incremental processing may be useful later, but introducing it during dashboard completion would create additional work and risk.

## 10. Scope is an engineering tool

Deferring a feature does not mean abandoning it. It means deciding that the feature is not currently worth the cost of implementing and maintaining it.

---

# Project Milestones

```text
Original dashboard idea
          ↓
Exploratory SQL and summary tables
          ↓
Central warehouse redesign
          ↓
Automated ETL
          ↓
Historical data-quality investigations
          ↓
Timestamp correction and anomaly handling
          ↓
Canonical song identity mapping
          ↓
MusicBrainz catalog enrichment
          ↓
Last.fm metadata and tag enrichment
          ↓
External enrichment integrated into ETL
          ↓
★ CURRENT: Dashboard Version 1.0.0 completion
          ↓
Future improvements after dashboard completion
```

The next major milestone is not another architecture rewrite.

It is completing, validating, and publishing the dashboard while keeping the underlying pipeline reliable.