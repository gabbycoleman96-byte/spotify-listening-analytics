Updating Spotify Extended Streaming History

Run this procedure only when a new Spotify Extended Streaming History export is received.

1. Preserve the current raw table

In MySQL:

RENAME TABLE listening_history_raw
TO listening_history_raw_backup_YYYY_MM_DD;

Use the actual date of the export/import.

2. Create the new raw table

CREATE TABLE listening_history_raw
LIKE listening_history_raw_backup_YYYY_MM_DD;

This gives the new table the exact same structure as the backup.

3. Replace the Spotify JSON files

Place the new Spotify Extended Streaming History JSON files in:

data/Spotify_json_files/

Make sure the folder contains the complete export before continuing.

4. Combine the JSON files

From the project root:

python -m utils.new_spotify_export.combine_spotify_jsons

This creates:

data/Spotify_json_files/listening_history_raw.csv

5. Load the combined CSV

From the project root:

python -m utils.new_spotify_export.load_listening_history_raw

This loads the Spotify export into:

listening_history_raw

6. Run the full ETL

From the project root:

python main.py

This rebuilds the warehouse and all downstream ETL outputs.

Order matters
Rename old raw table
        ↓
Create new raw table
        ↓
Replace Spotify JSON files
        ↓
combine_spotify_export.py
        ↓
load_spotify_export.py
        ↓
main.py
        ↓
Update canonical URIs
        ↓
Resolve unmatched liked songs

Do not skip the backup. The whole point is that if something goes sideways during the import or warehouse rebuild, we still have the previous raw dataset sitting there untouched.