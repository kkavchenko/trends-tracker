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


def test_pick_examples_returns_most_recent_deduped():
    rows = [
        {"tags": ["ai"], "url": "https://a.com/1", "title": "A", "source": "S", "scraped_at": "2026-07-01T00:00:00+00:00"},
        {"tags": ["ai"], "url": "https://a.com/2", "title": "B", "source": "S", "scraped_at": "2026-07-03T00:00:00+00:00"},
        {"tags": ["ai"], "url": "https://a.com/2", "title": "B dup", "source": "S", "scraped_at": "2026-07-03T00:00:00+00:00"},
        {"tags": ["other"], "url": "https://a.com/3", "title": "C", "source": "S", "scraped_at": "2026-07-04T00:00:00+00:00"},
    ]
    examples = digest.pick_examples(rows, "ai", limit=2)
    assert len(examples) == 2
    assert examples[0]["url"] == "https://a.com/2"
    assert examples[1]["url"] == "https://a.com/1"


def test_render_markdown_formats_entries_with_directions():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    entries = [
        {
            "tag": "ai", "this_count": 12, "last_count": 7, "direction": "↑",
            "examples": [{"title": "EU Finalizes AI Act", "url": "https://x.com/1", "source": "Wired AI"}],
        },
    ]
    md = digest.render_markdown(now, entries)
    assert "# News Tracker Digest — 2026-07-10" in md
    assert "### 1. ai — 12 articles this week (↑ from 7 last week)" in md
    assert "[EU Finalizes AI Act](https://x.com/1) — Wired AI" in md


def test_render_markdown_handles_zero_articles():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    md = digest.render_markdown(now, [])
    assert "No new articles in the last 7 days." in md
