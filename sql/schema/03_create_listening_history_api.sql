DROP TABLE IF EXISTS listening_history_api;

CREATE TABLE listening_history_api (

    played_at      DATETIME      NOT NULL,
    spotify_id     VARCHAR(30)   NOT NULL,
    spotify_uri    VARCHAR(60)   NOT NULL,

    track_name     VARCHAR(255),
    artist_name    VARCHAR(255),
    album_name     VARCHAR(255),

    duration_ms    INT,
    popularity     INT,
    explicit       BOOLEAN,

    PRIMARY KEY (played_at, spotify_id)

);
