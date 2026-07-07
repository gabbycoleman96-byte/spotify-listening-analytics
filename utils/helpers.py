"""
helpers.py

Reusable helper functions used throughout the Spotify ETL project.
"""


def normalize_release_date(release_date):
    """
    Convert Spotify release dates into a format accepted by MySQL.

    Spotify may return:

        YYYY
        YYYY-MM
        YYYY-MM-DD

    MySQL DATE requires:

        YYYY-MM-DD
    """

    if len(release_date) == 4:
        return f"{release_date}-01-01"

    if len(release_date) == 7:
        return f"{release_date}-01"

    return release_date