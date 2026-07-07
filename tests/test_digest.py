from datetime import datetime, timedelta, timezone

import digest


def test_split_windows_separates_this_and_last_week():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    rows = [
        {"scraped_at": (now - timedelta(days=1)).isoformat()},   # this week
        {"scraped_at": (now - timedelta(days=6)).isoformat()},   # this week
        {"scraped_at": (now - timedelta(days=8)).isoformat()},   # last week
        {"scraped_at": (now - timedelta(days=13)).isoformat()},  # last week
        {"scraped_at": (now - timedelta(days=20)).isoformat()},  # too old, excluded
    ]
    this_week, last_week = digest.split_windows(rows, now)
    assert len(this_week) == 2
    assert len(last_week) == 2


def test_count_tags_counts_each_tag_occurrence():
    rows = [
        {"tags": ["ai", "policy"]},
        {"tags": ["ai"]},
        {"tags": None},
        {"tags": []},
    ]
    counts = digest.count_tags(rows)
    assert counts["ai"] == 2
    assert counts["policy"] == 1
