# Design Decisions

## Purpose

This document records the major technical and architectural decisions behind Spotify Listening Analytics, including why those decisions were made, the trade-offs involved, and which improvements have been deliberately deferred.

The project has evolved from a Tableau dashboard into a personal data-engineering pipeline with a MySQL warehouse, reusable SQL analytics, Spotify metadata, external music metadata, data-quality rules, and automated exports.

The guiding priority for Dashboard Version 1.0.0 is **to finish a reliable analytical product without destabilizing the working pipeline**.

---

# Guiding Principles

The project follows these principles:

- **One analytical source of truth:** Shared listening-history analysis should use the central warehouse rather than independently maintained copies of business logic.
- **Preserve source data:** Cleaning and transformation should not destroy the original historical listening records.
- **Automate repetitive work:** Recurring data processing should require minimal manual intervention.
- **Separate responsibilities:** Extraction, transformation, enrichment, analytics, and presentation should have distinct roles.
- **Cache external data:** API-derived metadata should be stored locally so that repeated pipeline runs do not needlessly repeat lookups.
- **Prefer traceable decisions:** Data-quality rules, identity resolution, and enrichment results should be inspectable.
- **Distinguish suspicious from invalid:** Unusual behavior should not automatically be treated as incorrect data.
- **Avoid premature optimization:** A working, understandable system takes priority over performance improvements that introduce unnecessary risk.
- **Finish the current version before expanding scope:** New features should support an actual dashboard requirement or wait for a later version.

---

# 1. Why Build a Central Listening-History Warehouse?

## Decision

Use `listening_history_warehouse` as the primary analytical source for listening-history reporting.

## Rationale

The project originally relied on multiple purpose-built summary tables. That approach worked for individual questions, but each new dashboard idea created another place where analytical logic could be implemented.

A central warehouse makes it possible to reuse the same listening events across SQL analyses and Tableau visualizations.

It also provides a consistent place to apply timestamp corrections, cleaning rules, metadata enrichment, and listening-behavior calculations.

## Trade-off

The warehouse requires more transformation work than a collection of small summary tables. In exchange, it reduces duplicated logic and makes future analyses easier to build.

---

# 2. Why Preserve the Raw Listening History?

## Decision

Retain the imported historical Spotify data in `listening_history_raw` and perform cleaning in downstream processing.

## Rationale

Spotify's Extended Streaming History contains edge cases that may not become apparent until a specific metric or visualization is investigated.

Preserving the source data makes it possible to:

- Rebuild the warehouse after transformation rules change.
- Investigate suspicious playback patterns.
- Compare cleaned records with their original source values.
- Correct timestamp or deduplication logic without requiring another export.
- Maintain evidence when a record is flagged as anomalous.

## Trade-off

Keeping raw and transformed data requires additional storage. That cost is worthwhile because reproducibility and investigation are more valuable than saving a relatively small amount of database space.

---

# 3. Why Perform the Main Transformation in Python?

## Decision

Use Python and pandas for the main listening-history cleaning and transformation process, with MySQL handling persistent storage and SQL handling reusable analytics.

## Rationale

Python provides a centralized environment for processing the historical export and applying rules that involve multiple fields, timestamp interpretation, duplicate detection, and anomaly identification.

The transformation layer handles tasks such as:

- Cleaning and deduplication.
- Offline timestamp correction.
- Calendar and time-of-day dimensions.
- Track and artist identifier extraction.
- Metadata integration.
- Listening-event quality checks.
- Preparation of warehouse-ready records.

MySQL remains responsible for storing the resulting data and supporting relational joins and analytical queries.

## Trade-off

Some transformations could be implemented in SQL. Keeping the main cleaning logic in Python, however, provides a clear processing workflow and makes the rules easier to inspect in one place.

The project does not require every transformation to use the same language. The choice depends on the responsibility being handled.

---

# 4. Why Use Specific Duplicate-Removal Rules?

## Decision

Distinguish duplicate representations of a playback event from legitimate repeat listening.

### Exact duplicates

Identical records across the relevant playback fields are removed.

### Matching timestamp and track

When multiple records represent the same Spotify track at the same timestamp, the record with the greatest `ms_played` is retained.

### Rationale

Repeated listening is a normal part of music behavior. Removing records merely because the same track appears more than once would erase legitimate plays.

Using timestamp and track identity provides a more targeted way to identify duplicate representations while retaining separate playback events.

## Trade-off

No deduplication rule can guarantee perfect classification for every unusual source record. The rules are designed to remove likely duplicates without broadly suppressing repeat listening.

---

# 5. Why Remove Impossible Playback Events?

## Decision

Remove playback events that overlap an earlier valid playback of the same track beyond the configured tolerance.

## Rationale

Under the project's playback model, a track cannot ordinarily begin a new complete playback before the preceding playback of that same track could reasonably have finished.

The rule helps eliminate records that would distort listening counts and timeline analysis.

## Trade-off

This is a project-defined data-quality rule, not proof that Spotify's original record is invalid in every possible circumstance. Its behavior should be reconsidered if the playback model or source data changes.

---

# 6. Why Flag Anomalies Instead of Deleting Them?

## Decision

Retain suspicious repeating playback patterns when their status is uncertain and identify them with:

- `is_anomaly`
- `anomaly_type`

## Rationale

The project distinguishes between records that meet a defined removal rule and records that appear unusual but may still be meaningful.

The repeating playback sequence from July 5, 2022, involving five tracks, illustrated the problem. The pattern generated an implausibly high number of records and required investigation before its effect on analytical results could be understood.

Rather than silently deleting the underlying history, the project flags the pattern so downstream analyses can exclude or examine it deliberately.

## Trade-off

Keeping flagged events means that analytical queries must account for anomalies when they would distort a particular metric.

That additional responsibility is preferable to permanently discarding historical evidence based on an assumption.

---

# 7. Why Correct Offline Playback Timestamps?

## Decision

When `offline = true` and a valid `offline_timestamp` is available, use the offline timestamp to determine the canonical `played_at` value.

## Rationale

Spotify's raw `ts` can reflect synchronization timing rather than the actual time an offline track was played.

The historical export also contains `offline_timestamp` values represented at different Unix timestamp scales: seconds and milliseconds.

The transformation identifies the appropriate scale from the value's magnitude before converting it into a datetime.

All downstream calendar and time-of-day dimensions derive from `played_at`.

## Trade-off

Timestamp correction introduces additional transformation logic, but it prevents offline synchronization from distorting listening timelines and historical comparisons.

---

# 8. Why Use `played_at` as the Canonical Timestamp?

## Decision

Use `played_at` as the standardized playback timestamp throughout the warehouse.

## Rationale

If individual SQL queries and Tableau worksheets independently decide whether to use the raw `ts` or `offline_timestamp`, the same listening event could appear on different dates or at different times depending on the visualization.

Establishing `played_at` as the canonical timestamp creates a shared interpretation of when a listening event occurred.

Calendar dimensions, time-of-day analysis, and related temporal calculations should be derived from that standardized value.

---

# 9. Why Separate Spotify Metadata From Listening Events?

## Decision

Store reusable Spotify catalog metadata in dedicated tables rather than duplicating all catalog information across listening-history records.

Relevant tables include:

- `track_metadata`
- `artist_metadata`
- `album_metadata`
- `track_artists`

## Rationale

A track can appear in listening history many times. Storing its catalog metadata separately avoids repeatedly maintaining the same descriptive information across every playback event.

Dedicated metadata tables also allow catalog enrichment to be updated independently of historical listening records.

The `track_artists` relationship supports tracks associated with multiple artists rather than assuming every track has exactly one artist.

## Trade-off

Separate metadata tables require joins during warehouse enrichment and analytical queries. That added relational complexity supports better reuse and more consistent metadata management.

---

# 10. Why Introduce Song Identity Mapping?

## Decision

Maintain a song identity-resolution layer using `song_identity_map` and `canonical_song_uris`.

## Rationale

A song can appear under multiple Spotify track IDs because of alternate releases, reissues, remasters, regional releases, and other catalog variations.

Treating every Spotify ID as a completely unrelated song can fragment listening counts, liked-song status, and other analyses.

The identity layer provides a place to record canonical mappings and their resolution details rather than scattering identity assumptions throughout the warehouse and Tableau calculations.

The project also retains resolution information, including status, method, and reason, so identity decisions can be reviewed.

## Trade-off

Identity resolution introduces complexity and requires careful judgment. Different releases are not always interchangeable, and automatically combining tracks can produce misleading results.

Canonical mapping therefore needs to distinguish a supported identity decision from an unresolved or ambiguous match.

---

# 11. Why Prioritize the Earliest Known Release Date?

## Decision

For canonical song-version selection, use the earliest supported release date available from the project's metadata sources as an important selection criterion.

## Rationale

The Spotify catalog may contain multiple versions of what appears to be the same song. Selecting a canonical version consistently helps consolidate analysis across those variants.

MusicBrainz provides recording and release-related metadata that can supplement Spotify's catalog information. Its release-date precision is also recorded so that a year-only date is not treated as equivalent in certainty to a complete date.

## Trade-off

The earliest known release date is a useful selection criterion, but it is not sufficient on its own to prove that two track IDs represent the same recording.

Identity matching and canonical-version selection must remain separate decisions. Ambiguous cases should not be resolved solely by comparing dates.

---

# 12. Why Keep External Music Metadata in Separate Tables?

## Decision

Store MusicBrainz and Last.fm enrichment in dedicated tables rather than making the external sources part of the core listening-history transformation.

The current external metadata layer includes:

- `musicbrainz_track_metadata`
- `musicbrainz_artist_metadata`
- `lastfm_track_metadata`
- `lastfm_artist_metadata`
- `external_track_tags`
- `external_artist_tags`
- `lastfm_similar_tracks`

The corresponding enrichment scripts are separate from the core warehouse transformation.

## Rationale

The external sources serve different purposes:

**MusicBrainz** provides recording-oriented metadata and matching information, including recording identifiers and available release dates.

**Last.fm** provides listening statistics, descriptive information, tags, and a foundation for potential similar-track analysis.

Keeping this information separate makes it possible to enrich the catalog without changing the meaning or grain of the listening-history warehouse.

It also allows source-specific matching rules, lookup statuses, and API responses to be stored independently.

## Trade-off

The additional tables create more relationships to understand and maintain. They also make the system more flexible because external metadata can be updated or investigated without rebuilding the core listening history merely to store a lookup result.

---

# 13. Why Cache External API Results?

## Decision

Persist external enrichment results in MySQL and use lookup statuses and timestamps to manage subsequent processing.

## Rationale

External APIs have request limits, network dependencies, and source-specific matching behavior. Repeating the same lookup unnecessarily wastes requests and increases processing time.

The cache tables provide a persistent record of lookup outcomes, including successful matches, unsuccessful lookups, ambiguous results where applicable, and errors.

Tag data is stored separately so multiple tags can be associated with a track or artist and attributed to their source.

## Trade-off

Cached information can become outdated, and a failed or unsuccessful lookup does not necessarily mean that the source has no matching record.

The project must retain enough status information to distinguish an unsuccessful search from a successful match and a technical failure. Reprocessing policies can be refined as the enrichment workflow evolves.

---

# 14. Why Keep External Enrichment Separate From Core ETL Failures?

## Decision

Run external music enrichment as a distinct pipeline stage and allow the core pipeline to continue when an enrichment command reports a problem.

## Rationale

External metadata is valuable, but it is not required for every core listening-history operation.

A MusicBrainz or Last.fm outage should not automatically prevent the warehouse, SQL analytics, and Tableau exports from being refreshed.

The integration records a warning when an enrichment command fails, while the enrichment tables retain individual lookup outcomes.

## Trade-off

A successful pipeline run does not necessarily mean every external lookup succeeded. Overall pipeline status and individual enrichment statuses must be interpreted separately.

This design favors continued availability of the core analytical product while preserving visibility into enrichment problems.

---

# 15. Why Keep Genre Enrichment Separate From the Core Warehouse?

## Decision

Treat genre information as a distinct enrichment concern rather than assuming that every track already has reliable genre values.

## Rationale

Genre information is not uniformly available at the track level across the project's existing metadata sources. External tags can also differ in terminology, specificity, and popularity.

The external tag tables provide a place to store source-attributed descriptions without forcing every tag into a single standardized genre classification prematurely.

The warehouse currently contains `primary_genre` and `secondary_genre` fields, but those fields may remain unpopulated when no value is available from the current enrichment process.

## Trade-off

Leaving unavailable genre fields empty limits some visualizations in the short term. It avoids presenting invented or unsupported genre classifications as established facts.

A future classification process can derive standardized genres from external tags if a clear analytical requirement justifies it.

---

# 16. Why Rebuild the Warehouse Instead of Loading Incrementally?

## Decision

Continue rebuilding the warehouse from the transformed historical source during each pipeline run.

## Rationale

The rebuild approach is straightforward to reason about and allows changes to transformation rules to be applied consistently across the retained history.

This is particularly useful while the project is still refining timestamp handling, data-quality rules, identity mapping, and warehouse enrichment.

## Trade-off

A full rebuild takes more processing time than a carefully implemented incremental strategy.

Incremental loading would require additional logic for identifying changed records, applying revised transformation rules to existing data, and keeping derived fields and analytics consistent.

**Incremental warehouse processing is intentionally deferred.** The current priority is completing Dashboard Version 1.0.0 without introducing unnecessary risk into a working pipeline.

---

# 17. Why Use SQL for Reusable Analytics?

## Decision

Keep reusable analytical queries in the repository's SQL analytics layer and rebuild the configured summary tables through the pipeline.

## Rationale

SQL provides a repeatable way to calculate metrics from the warehouse and to prepare structured results for downstream reporting.

Centralizing shared calculations reduces the risk that the same metric will be defined differently in separate Tableau worksheets.

It also makes analytical logic easier to review, version, and reproduce.

## Trade-off

Not every visualization needs a dedicated summary table. The project should avoid creating new tables when a direct query or an existing analytical dataset is sufficient.

New analytical tables should solve a real reuse, performance, or presentation problem rather than simply add another layer of maintenance.

---

# 18. Why Export CSV Files for Tableau Public?

## Decision

Use CSV exports as the bridge between the MySQL/Python pipeline and Tableau Public.

## Rationale

CSV files are portable, easy to inspect, compatible with Tableau, and straightforward to regenerate after a pipeline run.

This approach avoids requiring Tableau Public to connect directly to the local MySQL database.

The pipeline exports the configured datasets, including the listening-history warehouse and selected analytical tables.

## Trade-off

CSV exports are snapshots rather than live database connections. Tableau data must be refreshed from the latest exports when the underlying data changes.

For the current portfolio project, the simplicity of this approach outweighs the benefits of introducing additional hosting or live database infrastructure.

---

# 19. Why Use Tableau Public?

## Decision

Use Tableau Public as the presentation layer for the project.

## Rationale

The project is intended to demonstrate both data-engineering capability and analytical storytelling.

Tableau Public provides a shareable presentation for the completed dashboards while keeping extraction, transformation, data quality, identity resolution, enrichment, and analytical preparation in the underlying codebase.

The dashboard is the primary user-facing deliverable for Version 1.0.0.

## Trade-off

Tableau Public imposes constraints compared with a fully hosted private analytics environment. The project accepts those constraints in exchange for straightforward portfolio presentation.

---

# 20. Why Reduce Dependence on Recently Played?

## Decision

The Recently Played endpoint is not a required stage in the current recurring workflow.

## Rationale

The current analytical foundation is the imported historical listening export, with the warehouse rebuilt from that source.

The project no longer requires the previous 30-minute Recently Played workflow to maintain the core dashboard dataset.

A lower-frequency schedule is sufficient for the current workflow and avoids unnecessary repeated processing.

## Trade-off

This design prioritizes historical listening analysis and stable dashboard refreshes rather than continuously capturing new listening events through the Recently Played endpoint.

If near-real-time listening analysis becomes a requirement again, it can be reconsidered as a separate ingestion concern.

---

# 21. Why Keep Execution Logging Separate From Analytical Data?

## Decision

Record pipeline execution results in `etl_log` rather than mixing operational status into the listening-history warehouse.

## Rationale

Pipeline health and listening behavior are different kinds of information.

The ETL log records details such as start time, end time, runtime, status, and error messages, alongside the supported high-level ingestion counts.

This makes it possible to review whether a run completed, how long it took, and whether it reported a failure or warning without changing the grain of listening-history records.

## Trade-off

The current log captures high-level execution information rather than a dedicated metric for every external enrichment operation.

Individual enrichment results remain in their corresponding cache tables, and more detailed operational monitoring can be introduced later if needed.

---

# 22. Why Use Windows Task Scheduler?

## Decision

Use Windows Task Scheduler to run the pipeline automatically on a recurring schedule.

## Rationale

Automation reduces the need to remember to execute the ETL manually and helps keep the warehouse and Tableau exports current.

The pipeline remains executable manually for development, troubleshooting, and one-off refreshes.

## Trade-off

The workflow depends on the local Windows environment and its configuration. Moving the pipeline to a hosted or server-based environment would require a separate deployment decision.

---

# 23. Current Stability Boundary

During Dashboard Version 1.0.0, the following changes are deferred unless they are necessary to satisfy a concrete dashboard requirement:

- Incremental warehouse loading.
- Major warehouse schema redesign.
- Broad ETL refactoring.
- Performance optimization unrelated to a current blocker.
- Additional external data sources without a defined use case.
- Large-scale changes to the core listening-history transformation.
- Automated playlist generation and direct Spotify playlist creation.
- Advanced recommendation logic that is not yet required by the dashboard.

This is an intentional scope boundary, not a claim that these improvements lack value.

> If the current system works and a dashboard requirement can be completed without changing it, leave the system alone.

---

# 24. Versioning Philosophy

## Pipeline Version 1.0.0

Established the automated extraction, transformation, loading, analytics, export, and logging workflow.

## Warehouse Version 1.1

Introduced additional warehouse fields and processing to support data quality, anomaly analysis, and dashboard requirements.

## Dashboard Version 1.0.0

The current priority.

Goals:

- Complete the planned dashboards.
- Validate KPIs and analytical definitions.
- Resolve data-quality filtering requirements.
- Polish interactions, navigation, and tooltips.
- Publish the portfolio-ready Tableau Public result.

## Future Versions

Potential improvements include:

- Incremental warehouse processing.
- Expanded metadata and genre enrichment.
- Further refinement of canonical song identity.
- Similar-track and recommendation analysis.
- More advanced anomaly detection.
- Automated playlist generation.
- Direct Spotify playlist creation.
- Additional operational monitoring.

These features should be prioritized after the current dashboard is complete or when a specific requirement makes them necessary.

---

# Summary

The architecture is designed around a consistent idea: preserve the source data, make analytical rules reusable, keep external enrichment traceable, and avoid unnecessary changes to a working pipeline.

The current rebuild strategy and local CSV exports are deliberate trade-offs in favor of simplicity and reliability. The separate identity and enrichment layers provide room for more advanced music analysis without forcing those concerns into the core listening-history table.

The next major milestone is completing Dashboard Version 1.0.0. Infrastructure improvements should support that goal rather than compete with it.
