"""
Generate a daily trend digest comparing this week's tag counts to last
week's, sourced entirely from the articles table's existing history
(no separate archive file is kept).
"""

from collections import Counter
from datetime import datetime, timedelta, timezone


def split_windows(rows, now):
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)
    this_week = []
    last_week = []
    for row in rows:
        scraped_at = datetime.fromisoformat(row["scraped_at"])
        if scraped_at >= this_week_start:
            this_week.append(row)
        elif scraped_at >= last_week_start:
            last_week.append(row)
    return this_week, last_week


def count_tags(rows):
    counter = Counter()
    for row in rows:
        for tag in (row.get("tags") or []):
            counter[tag] += 1
    return counter
