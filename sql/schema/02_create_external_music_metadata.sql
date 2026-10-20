
USE spotify_analysis;

-- ============================================================
-- 1. MusicBrainz recording metadata
-- One row per Spotify track ID.
-- ============================================================

CREATE TABLE IF NOT EXISTS musicbrainz_track_metadata (
    spotify_id VARCHAR(50) NOT NULL,
    recording_mbid CHAR(36) NULL,
    recording_title VARCHAR(500) NULL,
    recording_length_ms INT NULL,
    disambiguation VARCHAR(500) NULL,
    first_release_date VARCHAR(10) NULL,
    first_release_date_precision VARCHAR(10) NULL,
    artist_credit JSON NULL,
    release_mbids JSON NULL,
    match_method VARCHAR(30) NULL,
    match_score DECIMAL(6,5) NULL,
    lookup_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    lookup_message TEXT NULL,
    raw_response JSON NULL,
    last_checked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_id),
    INDEX idx_mb_recording_mbid (recording_mbid),
    INDEX idx_mb_track_status (lookup_status),
    INDEX idx_mb_first_release_date (first_release_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 2. MusicBrainz artist metadata
-- Maps Spotify artist IDs to MusicBrainz artist IDs.
-- ============================================================

CREATE TABLE IF NOT EXISTS musicbrainz_artist_metadata (
    spotify_artist_id VARCHAR(50) NOT NULL,
    artist_mbid CHAR(36) NULL,
    artist_name VARCHAR(500) NULL,
    disambiguation VARCHAR(500) NULL,
    artist_type VARCHAR(50) NULL,
    country VARCHAR(10) NULL,
    begin_date VARCHAR(10) NULL,
    end_date VARCHAR(10) NULL,
    match_method VARCHAR(30) NULL,
    match_score DECIMAL(6,5) NULL,
    lookup_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    lookup_message TEXT NULL,
    raw_response JSON NULL,
    last_checked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_artist_id),
    INDEX idx_mb_artist_mbid (artist_mbid),
    INDEX idx_mb_artist_status (lookup_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 3. Last.fm track metadata
-- Listeners and playcount are Last.fm community statistics,
-- NOT your personal Spotify listening counts.
-- ============================================================

CREATE TABLE IF NOT EXISTS lastfm_track_metadata (
    spotify_id VARCHAR(50) NOT NULL,
    lastfm_mbid CHAR(36) NULL,
    lastfm_track_url VARCHAR(1000) NULL,
    listeners BIGINT UNSIGNED NULL,
    playcount BIGINT UNSIGNED NULL,
    summary TEXT NULL,
    content TEXT NULL,
    lookup_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    lookup_message TEXT NULL,
    raw_response JSON NULL,
    last_checked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_id),
    INDEX idx_lastfm_track_mbid (lastfm_mbid),
    INDEX idx_lastfm_track_status (lookup_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 4. Last.fm artist metadata
-- ============================================================

CREATE TABLE IF NOT EXISTS lastfm_artist_metadata (
    spotify_artist_id VARCHAR(50) NOT NULL,
    lastfm_artist_name VARCHAR(500) NULL,
    lastfm_artist_url VARCHAR(1000) NULL,
    lastfm_mbid CHAR(36) NULL,
    listeners BIGINT UNSIGNED NULL,
    playcount BIGINT UNSIGNED NULL,
    summary TEXT NULL,
    content TEXT NULL,
    lookup_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    lookup_message TEXT NULL,
    raw_response JSON NULL,
    last_checked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_artist_id),
    INDEX idx_lastfm_artist_mbid (lastfm_mbid),
    INDEX idx_lastfm_artist_status (lookup_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 5. Track tags from multiple sources
-- Examples: shoegaze, synthpop, melancholic, summer.
-- A tag remains associated with its source.
-- ============================================================

CREATE TABLE IF NOT EXISTS external_track_tags (
    spotify_id VARCHAR(50) NOT NULL,
    source VARCHAR(30) NOT NULL,
    tag_name VARCHAR(255) NOT NULL,
    tag_count INT UNSIGNED NULL,
    tag_position SMALLINT UNSIGNED NULL,
    retrieved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_id, source, tag_name),
    INDEX idx_track_tag_name (tag_name),
    INDEX idx_track_tag_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 6. Artist tags from multiple sources
-- ============================================================

CREATE TABLE IF NOT EXISTS external_artist_tags (
    spotify_artist_id VARCHAR(50) NOT NULL,
    source VARCHAR(30) NOT NULL,
    tag_name VARCHAR(255) NOT NULL,
    tag_count INT UNSIGNED NULL,
    tag_position SMALLINT UNSIGNED NULL,
    retrieved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_artist_id, source, tag_name),
    INDEX idx_artist_tag_name (tag_name),
    INDEX idx_artist_tag_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 7. Last.fm similar tracks
-- Names are retained even when we cannot confidently map a
-- recommendation to one of your Spotify track IDs.
-- ============================================================

CREATE TABLE IF NOT EXISTS lastfm_similar_tracks (
    spotify_id VARCHAR(50) NOT NULL,
    result_position SMALLINT UNSIGNED NOT NULL,
    similar_track_name VARCHAR(500) NOT NULL,
    similar_artist_name VARCHAR(500) NOT NULL,
    similar_track_mbid CHAR(36) NULL,
    similar_artist_mbid CHAR(36) NULL,
    match_score DECIMAL(8,6) NULL,
    matched_spotify_id VARCHAR(50) NULL,
    retrieved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_id, result_position),
    INDEX idx_similar_track_mbid (similar_track_mbid),
    INDEX idx_similar_artist_mbid (similar_artist_mbid),
    INDEX idx_matched_spotify_id (matched_spotify_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Verification
-- ============================================================

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN (
      'musicbrainz_track_metadata',
      'musicbrainz_artist_metadata',
      'lastfm_track_metadata',
      'lastfm_artist_metadata',
      'external_track_tags',
      'external_artist_tags',
      'lastfm_similar_tracks'
  )
ORDER BY table_name;
