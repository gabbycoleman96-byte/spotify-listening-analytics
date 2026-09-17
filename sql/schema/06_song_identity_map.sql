-- Spotify Song Identity Map
-- One row per Spotify track ID known to the project.
--
-- spotify_id is case-sensitive because Spotify IDs are base62 strings.

CREATE TABLE song_identity_map (
    spotify_id VARCHAR(22)
        CHARACTER SET ascii
        COLLATE ascii_bin
        NOT NULL,

    canonical_spotify_id VARCHAR(22)
        CHARACTER SET ascii
        COLLATE ascii_bin
        NULL,

    resolution_status VARCHAR(30) NOT NULL,
    resolution_method VARCHAR(500) NULL,
    resolution_reason TEXT NULL,

    is_liked BOOLEAN NOT NULL DEFAULT FALSE,
    source_type VARCHAR(30) NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (spotify_id),

    KEY idx_song_identity_canonical (canonical_spotify_id),
    KEY idx_song_identity_liked (is_liked),
    KEY idx_song_identity_status (resolution_status)
);