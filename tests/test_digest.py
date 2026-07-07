from collections import Counter
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


def test_rank_tags_marks_growth_decline_steady_and_new():
    this_week = Counter({"ai": 12, "creator economy": 8, "nostalgia economy": 3, "old topic": 1})
    last_week = Counter({"ai": 7, "creator economy": 8, "old topic": 5})
    ranked = digest.rank_tags(this_week, last_week, top_n=10)
    by_tag = {e["tag"]: e for e in ranked}
    assert by_tag["ai"]["direction"] == "↑"
    assert by_tag["creator economy"]["direction"] == "→"
    assert by_tag["nostalgia economy"]["direction"] == "🆕"
    assert by_tag["old topic"]["direction"] == "↓"


def test_rank_tags_respects_top_n_limit():
    this_week = Counter({f"tag{i}": 10 - i for i in range(15)})
    last_week = Counter()
    ranked = digest.rank_tags(this_week, last_week, top_n=10)
    assert len(ranked) == 10
