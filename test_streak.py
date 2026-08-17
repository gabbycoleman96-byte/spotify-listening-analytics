from transform.warehouse_transform import build_warehouse_dataframe
import pandas as pd

df = build_warehouse_dataframe()

album_url = "https://raw.githubusercontent.com/gabbycoleman96-byte/spotify-listening-analytics/main/assets/album_art/6kZ42qRrzov54LcAk4onW9.jpg"

x = df[
    df["album_art_url"] == album_url
][
    [
        "album_name",
        "album_art_url",
        "date",
        "album_longest_streak_days",
    ]
].drop_duplicates().sort_values("date")

dates = sorted(x["date"].unique())

longest_run = []
current_run = [dates[0]]

for i in range(1, len(dates)):
    if dates[i] - dates[i - 1] == pd.Timedelta(days=1):
        current_run.append(dates[i])
    else:
        if len(current_run) > len(longest_run):
            longest_run = current_run
        current_run = [dates[i]]

if len(current_run) > len(longest_run):
    longest_run = current_run

print("\nLongest streak:")
print("Start:", longest_run[0])
print("End:", longest_run[-1])
print("Days:", len(longest_run))