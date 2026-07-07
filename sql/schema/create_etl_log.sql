/*
===============================================================
Create ETL Log Table
===============================================================
*/

USE spotify_analysis;

CREATE TABLE IF NOT EXISTS etl_log (

    run_id INT AUTO_INCREMENT PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,

    start_time DATETIME NOT NULL,

    end_time DATETIME NOT NULL,

    runtime_seconds DECIMAL(10,2) NOT NULL,

    status VARCHAR(20) NOT NULL,

    liked_downloaded INT,

    liked_inserted INT,

    recent_downloaded INT,

    recent_inserted INT,

    error_message TEXT

);