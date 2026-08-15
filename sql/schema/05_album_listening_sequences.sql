DROP TABLE IF EXISTS album_listening_sequences;

CREATE TABLE album_listening_sequences (
    sequence_id BIGINT AUTO_INCREMENT PRIMARY KEY,

    album_id VARCHAR(255) NOT NULL,
    album_name VARCHAR(255) NOT NULL,
    artist_name VARCHAR(255) NULL,
    album_art_url TEXT NULL,

    total_tracks INT NOT NULL,
    tracks_played INT NOT NULL,

    total_ms_played BIGINT NOT NULL DEFAULT 0,

    first_played_at DATETIME NOT NULL,
    last_played_at DATETIME NOT NULL,

    is_full_album_listen TINYINT(1) NOT NULL DEFAULT 0,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_album_id (album_id),
    INDEX idx_full_album (is_full_album_listen),
    INDEX idx_first_played (first_played_at)
);