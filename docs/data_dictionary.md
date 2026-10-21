# Data Dictionary

## 1. Purpose

This document describes the principal data tables used by Spotify Listening Analytics, including their roles, intended grain, important fields, and relationships.

The project separates raw Spotify listening records, Spotify catalog metadata, canonical song identity, external music metadata, warehouse analytics, and pipeline execution logs.

**Source of truth:** The actual database schema scripts and current SQL/Python implementation define the authoritative table structures. This document provides a practical reference and should be updated when the schema changes.

---

## 2. Data Model Overview

```text
Spotify Extended Streaming History
                 |
                 v
      listening_history_raw
                 |
                 v
      listening_history_warehouse
                 |
        +--------+---------+
        |                  |
        v                  v
   SQL Analytics      Tableau Exports


Spotify Catalog Metadata
        |
        +--> track_metadata
        +--> artist_metadata
        +--> album_metadata
        +--> track_artists


Spotify Track Identity
        |
        +--> song_identity_map
        +--> canonical_song_uris


External Music Metadata
        |
        +--> musicbrainz_track_metadata
        +--> musicbrainz_artist_metadata
        +--> lastfm_track_metadata
        +--> lastfm_artist_metadata
        +--> external_track_tags
        +--> external_artist_tags
        +--> lastfm_similar_tracks


Pipeline Monitoring
        |
        +--> etl_log
```

The diagram shows logical relationships rather than a complete foreign-key diagram. Not every relationship is enforced by a database foreign key.

---

## 3. Raw Listening History

### `listening_history_raw`

**Purpose:** Preserve the imported Spotify Extended Streaming History records used to build the analytical warehouse.

**Grain:** One row per imported source playback record.

This table retains source fields that may be removed, renamed, or transformed downstream.

Important source fields include:

| Field | Description |
|---|---|
| `raw_id` | Database-generated identifier for a raw record |
| `ts` | Spotify source timestamp |
| `ms_played` | Playback duration reported by Spotify, in milliseconds |
| `master_metadata_track_name` | Source track name |
| `master_metadata_album_artist_name` | Source album-artist name |
| `master_metadata_album_album_name` | Source album name |
| `spotify_track_uri` | Spotify track URI when present |
| `offline` | Whether the source marks the playback as offline |
| `offline_timestamp` | Timestamp associated with offline playback when supplied |
| `source` | Source classification used by the project |

The export also includes other fields relating to playback context, device/platform, shuffle, skips, and non-music content. The exact columns depend on the current raw table definition.

**Important:** Warehouse cleaning does not replace the raw table's role as the preserved source dataset.

---

## 4. Analytical Warehouse

### `listening_history_warehouse`

**Purpose:** Provide the primary analytical dataset for listening-history calculations and Tableau reporting.

**Grain:** One retained listening event per row after transformation and data-quality rules.

The warehouse combines playback events with derived dimensions, Spotify identifiers, metadata, and analytical fields.

#### Main field groups

| Group | Representative fields | Purpose |
|---|---|---|
| Playback time | `played_at`, `date`, `year`, `quarter`, `month_number`, `month_name`, `week`, `day` | Calendar-based analysis |
| Time of day | `hour`, `hour_label`, `time` | Hourly and time-of-day analysis |
| Playback details | `ms_played`, `duration_ms`, `shuffle_state`, `skipped` | Playback behavior and duration |
| Music identity | `track_name`, `artist_name`, `album_name`, `spotify_id`, `spotify_uri` | Track and catalog identification |
| Listening context | `source`, `imported_at` | Record provenance and import timing |
| Library and artwork | `is_liked`, `album_art_url` | Library and visual presentation |
| Genre and color placeholders | `primary_genre`, `secondary_genre`, `dominant_color` | Dashboard-supporting enrichment fields |
| Quality | `is_anomaly`, `anomaly_type` | Flag suspicious playback patterns |
| Session analysis | `session_id`, `session_start`, `session_end`, `session_duration_minutes`, `session_stream_count` | Group playback into sessions |
| Navigation | `previous_track`, `next_track`, corresponding artist and album fields | Adjacent listening events |
| Sequence analysis | `play_number`, `play_of_day`, `play_of_week`, `play_of_month`, `play_of_year` | Listening sequence and ordinal calculations |
| Running counts | `artist_play_count`, `album_play_count`, `track_play_count` | Counts within listening sequences |

The warehouse also contains fields for streaks, session position, album-art usage, and comparisons with preceding or following plays.

This is a functional field guide, not a guarantee that every field is populated for every row. Some enrichment fields are currently placeholders or may be null when their source information is unavailable.

#### Important timestamp distinction

`played_at` is the canonical playback timestamp used to derive warehouse date and time dimensions. When a valid offline timestamp is used, the resulting calendar dimensions reflect the corrected playback time rather than blindly relying on the original source timestamp.

#### Rebuild behavior

The current pipeline rebuilds the warehouse from the raw source and subsequently rebuilds warehouse enrichment. It is not an incremental-only event table.

---

## 5. Spotify Catalog Metadata

### `track_metadata`

**Purpose:** Store Spotify track metadata used by the warehouse and downstream analytics.

**Logical key:** Spotify track ID.

The table supports retrieval of missing track metadata and is joined to album metadata for fields such as track duration and artwork.

Important identifiers include `spotify_id` and the associated album identifier. Consult the current schema for the complete set of track attributes.

### `artist_metadata`

**Purpose:** Store Spotify artist metadata.

**Logical key:** Spotify artist ID.

The artist metadata loader uses the `artist_id` and `scraped_at` fields to identify artists that require metadata retrieval.

### `album_metadata`

**Purpose:** Store album-level Spotify metadata and artwork information.

**Logical key:** Spotify album ID.

The warehouse enrichment process uses the album relationship to retrieve artwork information. The artwork manager updates the table with hosted image URLs.

### `track_artists`

**Purpose:** Represent the relationship between Spotify tracks and their credited artists.

This relationship supports tracks with multiple artists and provides the artist IDs used to identify missing artist metadata.

The table is used when selecting distinct artists that appear in the track catalog.

---

## 6. Song Identity Tables

### `song_identity_map`

**Purpose:** Maintain the project's permanent mapping between Spotify track IDs and accepted canonical song identities.

**Grain:** One row per Spotify track ID known to the identity map.

The table is defined in `sql/schema/06_song_identity_map.sql`.

| Field | Description |
|---|---|
| `spotify_id` | Spotify track ID represented by the row |
| `canonical_spotify_id` | Canonical Spotify track ID assigned to the identity group, when resolved |
| `resolution_status` | Status of the identity decision |
| `resolution_method` | Method or basis used for the decision |
| `resolution_reason` | Explanation supporting the decision |
| `is_liked` | Whether the identity record is marked as liked |
| `source_type` | Source classification associated with the identity record |
| `created_at` | Record creation timestamp |
| `updated_at` | Most recent record update timestamp |

The `spotify_id` column uses a case-sensitive ASCII collation because Spotify IDs are case-sensitive Base62 strings.

The map is built from accepted decisions in `data/investigative/song_identity_review.csv`. The build script does not repeat the original identity investigation.

### `canonical_song_uris`

**Purpose:** Provide a compatibility mapping from Spotify track IDs to canonical Spotify URIs.

This table is rebuilt from `song_identity_map` by `transform/apply_canonical_song_uris.py`.

| Field | Description |
|---|---|
| `spotify_id` | Spotify track ID represented by the mapping |
| `canonical_uri` | URI constructed from the canonical Spotify track ID |
| `version_count` | Number of Spotify IDs associated with the canonical identity |

The mapping is used by the pipeline when applying canonical identities and evaluating liked status.

**Identity distinction:** Canonical song identity is not the same as MusicBrainz recording identity. Alternate versions may belong to the same canonical song group while still representing different recordings.

---

## 7. MusicBrainz Metadata

The external music metadata schema is defined in:

`sql/schema/02_create_external_music_metadata.sql`

### `musicbrainz_track_metadata`

**Purpose:** Cache MusicBrainz recording metadata matched to Spotify tracks.

**Grain:** One row per Spotify track ID.

| Field | Description |
|---|---|
| `spotify_id` | Spotify track ID |
| `recording_mbid` | Matched MusicBrainz recording identifier |
| `recording_title` | MusicBrainz recording title |
| `recording_length_ms` | Recording length in milliseconds when available |
| `disambiguation` | Additional text distinguishing the recording |
| `first_release_date` | Earliest available release date from the lookup |
| `first_release_date_precision` | Precision of the available release date |
| `artist_credit` | JSON artist-credit information |
| `release_mbids` | JSON collection of release identifiers |
| `match_method` | Method used to obtain the match |
| `match_score` | Match confidence score |
| `lookup_status` | Outcome of the lookup |
| `lookup_message` | Additional lookup information |
| `raw_response` | Stored API response when available |
| `last_checked_at` | Most recent lookup timestamp |
| `created_at`, `updated_at` | Record lifecycle timestamps |

The table has indexes for the recording MBID, lookup status, and first release date.

The enrichment script evaluates recording candidates using title, artist-credit, and duration evidence where available. Not every Spotify track is guaranteed to receive a match.

### `musicbrainz_artist_metadata`

**Purpose:** Map Spotify artist IDs to MusicBrainz artist identities.

**Grain:** One row per Spotify artist ID.

Important fields include:

- `spotify_artist_id`
- `artist_mbid`
- `artist_name`
- `disambiguation`
- `artist_type`
- `country`
- `begin_date`
- `end_date`
- `match_method`
- `match_score`
- `lookup_status`
- `lookup_message`
- `raw_response`
- `last_checked_at`
- `created_at`
- `updated_at`

The table is defined in the schema, but the current main enrichment stage specifically invokes the MusicBrainz **track** enrichment script. The presence of this table does not mean that a full MusicBrainz artist-enrichment workflow is currently orchestrated.

---

## 8. Last.fm Metadata

Last.fm metadata is cached separately from Spotify catalog metadata and MusicBrainz recording matches.

### `lastfm_track_metadata`

**Purpose:** Store Last.fm track lookup results associated with Spotify tracks.

**Grain:** One row per Spotify track ID.

| Field | Description |
|---|---|
| `spotify_id` | Spotify track ID |
| `lastfm_mbid` | Last.fm-associated MusicBrainz recording identifier, when available |
| `lastfm_track_url` | Last.fm track page URL |
| `listeners` | Last.fm community listener count |
| `playcount` | Last.fm community play count |
| `summary` | Available summary text |
| `content` | Available longer description |
| `lookup_status` | Lookup outcome |
| `lookup_message` | Additional lookup information |
| `raw_response` | API response storage field |
| `last_checked_at` | Most recent lookup timestamp |
| `created_at`, `updated_at` | Record lifecycle timestamps |

Last.fm statistics describe Last.fm community activity. They are not personal Spotify listening totals.

### `lastfm_artist_metadata`

**Purpose:** Store Last.fm artist lookup results associated with Spotify artists.

**Grain:** One row per Spotify artist ID.

Important fields include:

- `spotify_artist_id`
- `lastfm_artist_name`
- `lastfm_artist_url`
- `lastfm_mbid`
- `listeners`
- `playcount`
- `summary`
- `content`
- `lookup_status`
- `lookup_message`
- `raw_response`
- `last_checked_at`
- `created_at`
- `updated_at`

### Lookup status interpretation

The Last.fm enrichment script reports statuses such as `matched`, `not_found`, and `error`.

A successful lookup does not necessarily mean tags were returned. Metadata can be useful even when the tag list is empty.

---

## 9. External Tag Tables

### `external_track_tags`

**Purpose:** Store track tags from one or more external sources while preserving source attribution.

**Grain:** One row per combination of Spotify track ID, tag source, and tag name.

| Field | Description |
|---|---|
| `spotify_id` | Spotify track ID |
| `source` | Source providing the tag, such as Last.fm |
| `tag_name` | Tag label |
| `tag_count` | Source-provided count when available |
| `tag_position` | Position in the source's tag list |
| `retrieved_at` | When the tag was retrieved |

**Primary key:** `(spotify_id, source, tag_name)`

This design allows the same tag to be associated with the same track from different sources without collapsing their provenance.

### `external_artist_tags`

**Purpose:** Store artist tags from external sources.

**Grain:** One row per combination of Spotify artist ID, tag source, and tag name.

| Field | Description |
|---|---|
| `spotify_artist_id` | Spotify artist ID |
| `source` | Tag source |
| `tag_name` | Tag label |
| `tag_count` | Source-provided count when available |
| `tag_position` | Position in the source's tag list |
| `retrieved_at` | When the tag was retrieved |

**Primary key:** `(spotify_artist_id, source, tag_name)`

The tag tables are intended to support genre-like classification and music discovery without forcing all external tags into a single canonical genre field.

---

## 10. Similar Tracks

### `lastfm_similar_tracks`

**Purpose:** Store Last.fm similar-track recommendations associated with a Spotify source track.

**Grain:** One row per source Spotify track and recommendation position.

| Field | Description |
|---|---|
| `spotify_id` | Spotify track for which recommendations were requested |
| `result_position` | Position in the returned recommendation list |
| `similar_track_name` | Recommended track name |
| `similar_artist_name` | Recommended artist name |
| `similar_track_mbid` | MusicBrainz identifier for the recommended track when available |
| `similar_artist_mbid` | MusicBrainz identifier for the recommended artist when available |
| `match_score` | Matching score when available |
| `matched_spotify_id` | Spotify track ID matched to the recommendation when possible |
| `retrieved_at` | Retrieval timestamp |

Recommended track names are retained even when a confident mapping to a Spotify track ID cannot be established.

The table is defined for recommendation enrichment. Its presence alone does not imply that similar-track retrieval is part of the current main ETL run.

---

## 11. Liked Songs

### `liked_songs`

**Purpose:** Store the user's Spotify liked-song library for library analysis and liked-status calculations.

The liked-song extraction stage checks the existing library state and loads newly retrieved records with duplicate protection.

The warehouse enrichment logic uses the liked-song data together with canonical URI mappings to derive `is_liked`.

The precise set of columns should be checked against the current liked-songs schema and extraction code.

---

## 12. Analytics and Tableau Exports

The analytics layer consists of SQL scripts under `sql/analysis/` and the tables those scripts build or refresh.

### `artist_summary`

A summary dataset used for artist-level reporting. Its exact calculations and columns are defined by the current SQL implementation.

### `album_listening_sequences`

A dataset used for album-sequence analysis. Its grain and sequence-classification rules are defined by the corresponding SQL implementation.

### Export configuration

`config/pipeline.py` defines the current export list:

- `listening_history_warehouse`
- `artist_summary`
- `liked_songs`
- `album_listening_sequences`

The export module writes each configured table to CSV for use in Tableau Public.

These are reporting outputs, not substitutes for the raw history or the underlying metadata tables.

---

## 13. ETL Execution Log

### `etl_log`

**Purpose:** Record high-level execution details for each run of the main ETL pipeline.

The table is defined in `sql/schema/03_create_etl_log.sql`.

| Field | Description |
|---|---|
| `run_id` | Auto-incrementing execution identifier |
| `pipeline_name` | Name of the pipeline |
| `start_time` | Run start timestamp |
| `end_time` | Run end timestamp |
| `runtime_seconds` | Total run duration in seconds |
| `status` | Overall pipeline status |
| `liked_downloaded` | Number of liked-song records downloaded |
| `liked_inserted` | Number of liked-song records inserted |
| `recent_downloaded` | Number of recent-track records downloaded when that stage runs |
| `recent_inserted` | Number of recent-track records inserted when that stage runs |
| `error_message` | Error or warning details when supplied |

The recent-track columns remain in the schema even though the Recently Played stage is currently disabled in `main.py`.

The logger can record `Success`, `Warning`, or `Failed` depending on the outcome reported by the pipeline.

The log records high-level stage outcomes. Individual MusicBrainz and Last.fm lookup results are stored in their respective metadata cache tables.

---

## 14. Relationships and Join Guidance

The principal relationships are logical associations through identifiers:

| From | To | Relationship |
|---|---|---|
| `listening_history_raw` | `listening_history_warehouse` | Raw playback records are transformed into retained analytical events |
| `track_metadata` | `album_metadata` | Track records reference album metadata |
| `track_artists` | `artist_metadata` | Track-to-artist relationships identify artist metadata |
| `song_identity_map` | `canonical_song_uris` | Canonical URI mapping is derived from accepted identity groups |
| `listening_history_warehouse` | `liked_songs` | Used with canonical identities to derive liked status |
| Spotify track IDs | `musicbrainz_track_metadata` | Track enrichment cache |
| Spotify artist IDs | `musicbrainz_artist_metadata` | Artist identity cache |
| Spotify track IDs | `lastfm_track_metadata` | Last.fm track cache |
| Spotify artist IDs | `lastfm_artist_metadata` | Last.fm artist cache |
| Track IDs and source | `external_track_tags` | Source-attributed track tags |
| Artist IDs and source | `external_artist_tags` | Source-attributed artist tags |
| Spotify track IDs | `lastfm_similar_tracks` | Similar-track recommendations |

These relationships describe how the application uses the tables. They should not be interpreted as a guarantee that all joins are enforced by foreign-key constraints.

---

## 15. Data Interpretation Notes

### Spotify track ID versus canonical song ID

A Spotify track ID identifies a catalog entry. The canonical identity map groups accepted entries that the project treats as the same underlying song.

### Canonical song identity versus recording identity

The canonical song map and MusicBrainz recording MBID serve different purposes. Alternate recordings can belong to the same song identity group while remaining distinct recordings.

### Raw timestamp versus playback timestamp

The raw source timestamp is preserved in the raw table. The warehouse's `played_at` value is the timestamp used for analytical calendar dimensions and may be corrected using offline playback data.

### Personal versus community statistics

Personal listening counts are derived from the user's listening-history records. Last.fm listeners and play counts are external community statistics and must be labeled separately in analytics.

### Missing metadata versus failed lookup

A null metadata field does not necessarily mean a lookup failed. Some source records legitimately lack a field, and a successful API lookup can return no tags or no release date. Lookup status should be considered alongside the field value.

### Historical snapshots

Record counts and date coverage change when a new Spotify export is loaded. Use current database queries for present-day counts rather than relying on historical figures in the project journal.

---

## 16. Keeping This Document Current

When the schema changes:

1. Check the relevant SQL schema file.
2. Check the Python modules that read or write the table.
3. Update the table's purpose, grain, keys, and important fields here.
4. Verify that the documented relationships match the actual joins.
5. Distinguish implemented functionality from tables or features that are only prepared for future use.

The database schema and implementation remain authoritative when this document and the code differ.