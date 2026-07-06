# Trend Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a daily `digest.md` file, auto-committed by a scheduled GitHub Actions workflow, that ranks trending tags and shows week-over-week growth/decline for each — sourced entirely from the existing `articles` table (no separate archive needed).

**Architecture:** A new `scripts/digest.py` pulls the last 14 days of articles from Supabase, splits them into "this week" / "last week" windows, ranks tags by this week's count, computes a growth indicator per tag by comparing to last week's count, attaches example articles, and renders markdown to `digest.md`. A new `.github/workflows/digest.yml` runs it daily and commits the result. Pure logic (windowing, counting, ranking, formatting) is unit-tested with `pytest`; the Supabase I/O and the workflow itself are verified by manual/live runs, matching how the rest of this codebase is tested today.

**Tech Stack:** Python 3.9+ (matches existing scripts), `pytest` (new dev dependency — first tests in this repo), `supabase-py`, `python-dotenv`, GitHub Actions.

---

## File structure

- **Create:** `scripts/digest.py` — all digest logic (pure functions) + `main()` I/O glue.
- **Create:** `tests/conftest.py` — makes `scripts/` importable from tests.
- **Create:** `tests/test_digest.py` — unit tests for every pure function in `digest.py`.
- **Create:** `.github/workflows/digest.yml` — daily scheduled workflow.
- **Modify:** `requirements.txt` — add `pytest`.

Unlike the existing scripts (`fetch_rss.py`, `tag_articles.py`, `trends.py`), which create their Supabase client at module import time, `digest.py` defers `load_dotenv()` and `create_client()` into `main()`. This is a deliberate, isolated difference (not a repo-wide refactor) needed so the pure functions can be imported and unit-tested without requiring real environment variables to be set.

---

### Task 1: Test infrastructure

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/digest.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Add pytest to requirements.txt**

Append to `requirements.txt`:
```
pytest==8.3.3
```

- [ ] **Step 2: Install it into the local venv**

Run: `cd news-tracker && source venv/bin/activate && pip install pytest==8.3.3`
Expected: `Successfully installed pytest-8.3.3 ...` (plus its dependencies like `iniconfig`, `pluggy`)

- [ ] **Step 3: Create an empty digest.py module stub**

Create `scripts/digest.py`:
```python
"""
Generate a daily trend digest comparing this week's tag counts to last
week's, sourced entirely from the articles table's existing history
(no separate archive file is kept).
"""
```

- [ ] **Step 4: Create tests/conftest.py so tests can import scripts/digest.py**

Create `tests/conftest.py`:
```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
```

- [ ] **Step 5: Verify pytest runs and collects zero tests without error**

Run: `pytest tests/ -v`
Expected: `collected 0 items` and exit code 0 (no errors)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt scripts/digest.py tests/conftest.py
git commit -m "Add pytest and digest.py test scaffolding"
```

---

### Task 2: `split_windows`

**Files:**
- Modify: `scripts/digest.py`
- Modify: `tests/test_digest.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_digest.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_digest.py::test_split_windows_separates_this_and_last_week -v`
Expected: FAIL with `AttributeError: module 'digest' has no attribute 'split_windows'`

- [ ] **Step 3: Implement split_windows**

Add to `scripts/digest.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_digest.py::test_split_windows_separates_this_and_last_week -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py tests/test_digest.py
git commit -m "Add split_windows for digest.py"
```

---

### Task 3: `count_tags`

**Files:**
- Modify: `scripts/digest.py`
- Modify: `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_digest.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_digest.py::test_count_tags_counts_each_tag_occurrence -v`
Expected: FAIL with `AttributeError: module 'digest' has no attribute 'count_tags'`

- [ ] **Step 3: Implement count_tags**

Add to `scripts/digest.py`:
```python
from collections import Counter


def count_tags(rows):
    counter = Counter()
    for row in rows:
        for tag in (row.get("tags") or []):
            counter[tag] += 1
    return counter
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_digest.py::test_count_tags_counts_each_tag_occurrence -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py tests/test_digest.py
git commit -m "Add count_tags for digest.py"
```

---

### Task 4: `rank_tags`

**Files:**
- Modify: `scripts/digest.py`
- Modify: `tests/test_digest.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_digest.py`:
```python
from collections import Counter


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_digest.py::test_rank_tags_marks_growth_decline_steady_and_new tests/test_digest.py::test_rank_tags_respects_top_n_limit -v`
Expected: FAIL with `AttributeError: module 'digest' has no attribute 'rank_tags'`

- [ ] **Step 3: Implement rank_tags**

Add to `scripts/digest.py`:
```python
def rank_tags(this_week_counts, last_week_counts, top_n=10):
    ranked = []
    for tag, this_count in this_week_counts.most_common(top_n):
        last_count = last_week_counts.get(tag, 0)
        if last_count == 0:
            direction = "🆕"
        elif this_count > last_count:
            direction = "↑"
        elif this_count < last_count:
            direction = "↓"
        else:
            direction = "→"
        ranked.append({
            "tag": tag,
            "this_count": this_count,
            "last_count": last_count,
            "direction": direction,
        })
    return ranked
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_digest.py::test_rank_tags_marks_growth_decline_steady_and_new tests/test_digest.py::test_rank_tags_respects_top_n_limit -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py tests/test_digest.py
git commit -m "Add rank_tags with week-over-week direction indicator"
```

---

### Task 5: `pick_examples`

**Files:**
- Modify: `scripts/digest.py`
- Modify: `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_digest.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_digest.py::test_pick_examples_returns_most_recent_deduped -v`
Expected: FAIL with `AttributeError: module 'digest' has no attribute 'pick_examples'`

- [ ] **Step 3: Implement pick_examples**

Add to `scripts/digest.py`:
```python
def pick_examples(this_week_rows, tag, limit=2):
    matches = [r for r in this_week_rows if tag in (r.get("tags") or [])]
    matches.sort(key=lambda r: datetime.fromisoformat(r["scraped_at"]), reverse=True)
    seen = set()
    examples = []
    for r in matches:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        examples.append(r)
        if len(examples) >= limit:
            break
    return examples
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_digest.py::test_pick_examples_returns_most_recent_deduped -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py tests/test_digest.py
git commit -m "Add pick_examples for digest.py"
```

---

### Task 6: `render_markdown`

**Files:**
- Modify: `scripts/digest.py`
- Modify: `tests/test_digest.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_digest.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_digest.py::test_render_markdown_formats_entries_with_directions tests/test_digest.py::test_render_markdown_handles_zero_articles -v`
Expected: FAIL with `AttributeError: module 'digest' has no attribute 'render_markdown'`

- [ ] **Step 3: Implement render_markdown**

Add to `scripts/digest.py`:
```python
def render_markdown(now, entries):
    date_str = now.strftime("%Y-%m-%d")
    if not entries:
        return f"# News Tracker Digest — {date_str}\n\nNo new articles in the last 7 days.\n"

    lines = [f"# News Tracker Digest — {date_str}", "", "## Top Trends (this week vs. last week)", ""]
    for i, entry in enumerate(entries, start=1):
        tag = entry["tag"]
        this_count = entry["this_count"]
        last_count = entry["last_count"]
        direction = entry["direction"]
        plural = "s" if this_count != 1 else ""
        if direction == "🆕":
            note = "🆕 new this week"
        elif direction == "→":
            note = f"→ steady, was {last_count} last week"
        elif direction == "↑":
            note = f"↑ from {last_count} last week"
        else:
            note = f"↓ from {last_count} last week"

        lines.append(f"### {i}. {tag} — {this_count} article{plural} this week ({note})")
        for article in entry["examples"]:
            lines.append(f"- [{article['title']}]({article['url']}) — {article['source']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_digest.py::test_render_markdown_formats_entries_with_directions tests/test_digest.py::test_render_markdown_handles_zero_articles -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py tests/test_digest.py
git commit -m "Add render_markdown for digest.py"
```

---

### Task 7: `build_digest_entries` (composition)

**Files:**
- Modify: `scripts/digest.py`
- Modify: `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_digest.py`:
```python
def test_build_digest_entries_attaches_examples():
    this_week_rows = [
        {"tags": ["ai"], "url": "https://x.com/1", "title": "T1", "source": "S", "scraped_at": "2026-07-09T00:00:00+00:00"},
    ]
    last_week_rows = []
    entries = digest.build_digest_entries(this_week_rows, last_week_rows)
    assert entries[0]["tag"] == "ai"
    assert entries[0]["direction"] == "🆕"
    assert entries[0]["examples"][0]["url"] == "https://x.com/1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_digest.py::test_build_digest_entries_attaches_examples -v`
Expected: FAIL with `AttributeError: module 'digest' has no attribute 'build_digest_entries'`

- [ ] **Step 3: Implement build_digest_entries**

Add to `scripts/digest.py`:
```python
def build_digest_entries(this_week_rows, last_week_rows, top_n=10, examples_per_tag=2):
    this_counts = count_tags(this_week_rows)
    last_counts = count_tags(last_week_rows)
    ranked = rank_tags(this_counts, last_counts, top_n=top_n)
    for entry in ranked:
        entry["examples"] = pick_examples(this_week_rows, entry["tag"], limit=examples_per_tag)
    return ranked
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_digest.py::test_build_digest_entries_attaches_examples -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to confirm nothing broke**

Run: `pytest tests/ -v`
Expected: All tests pass (8 passed)

- [ ] **Step 6: Commit**

```bash
git add scripts/digest.py tests/test_digest.py
git commit -m "Add build_digest_entries to compose ranking and examples"
```

---

### Task 8: Supabase I/O and `main()`

**Files:**
- Modify: `scripts/digest.py`

This task is not unit-tested (would require mocking Supabase, which no other script in this codebase does) — it's verified by a real local run in Task 9, consistent with how `fetch_rss.py`/`tag_articles.py`/`trends.py` are tested in this project.

- [ ] **Step 1: Add fetch_recent_articles and main()**

Add to `scripts/digest.py`:
```python
import os

from dotenv import load_dotenv


def fetch_recent_articles(sb, days=14):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        sb.table("articles")
        .select("tags, title, url, source, scraped_at")
        .gte("scraped_at", since)
        .execute()
    )
    return result.data


def main():
    load_dotenv()
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    now = datetime.now(timezone.utc)
    rows = fetch_recent_articles(sb, days=14)
    this_week_rows, last_week_rows = split_windows(rows, now)
    entries = build_digest_entries(this_week_rows, last_week_rows)
    markdown = render_markdown(now, entries)
    with open("digest.md", "w") as f:
        f.write(markdown)
    print(f"Wrote digest.md with {len(entries)} trending tags.")


if __name__ == "__main__":
    main()
```

Note: place the `import os` and `from dotenv import load_dotenv` lines at the top of the file alongside the existing imports (`from collections import Counter`, `from datetime import ...`), not inline mid-file — this listing shows what to add, not where every line physically goes.

- [ ] **Step 2: Run the full test suite once more to confirm the new I/O code didn't break imports**

Run: `pytest tests/ -v`
Expected: All 8 tests still pass

- [ ] **Step 3: Commit**

```bash
git add scripts/digest.py
git commit -m "Add Supabase fetch and main() entrypoint to digest.py"
```

---

### Task 9: Local end-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Run digest.py against the real Supabase project**

Run: `cd news-tracker && source venv/bin/activate && python scripts/digest.py`
Expected: `Wrote digest.md with N trending tags.` printed, and a `digest.md` file created at the repo root.

- [ ] **Step 2: Inspect the generated file**

Run: `cat digest.md`
Expected: Markdown matching the format from the design spec — a `# News Tracker Digest — <today's date>` header, ranked tags with direction indicators, and example article links. (If fewer than 7 days of tagged history exist yet, some tags may show `🆕` for all entries — that's correct given the actual data, not a bug.)

- [ ] **Step 3: Confirm digest.md is not accidentally gitignored**

Run: `git check-ignore digest.md; echo "exit code: $?"`
Expected: `exit code: 1` (not ignored — `.gitignore` only excludes `.env`, `venv/`, `__pycache__/`, `*.pyc`, `.DS_Store`)

---

### Task 10: `digest.yml` workflow

**Files:**
- Create: `.github/workflows/digest.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/digest.yml`:
```yaml
name: digest

on:
  schedule:
    - cron: '0 8 * * *'  # daily at 8am UTC
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install supabase python-dotenv

      - name: Generate digest
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: python scripts/digest.py

      - name: Commit digest.md
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add digest.md
          if git diff --cached --quiet; then
            echo "No changes to digest.md, skipping commit."
          else
            git commit -m "Update daily digest"
            git push
          fi
```

- [ ] **Step 2: Commit and push (this file, plus digest.md from Task 9, plus everything from Tasks 1-8)**

```bash
git add .github/workflows/digest.yml digest.md
git commit -m "Add daily digest workflow"
git push
```

---

### Task 11: Verify the workflow runs in CI

**Files:** none (verification only)

- [ ] **Step 1: Manually trigger the workflow**

Run: `gh workflow run digest.yml --repo kkavchenko/news-tracker`

- [ ] **Step 2: Watch it to completion**

Run:
```bash
sleep 8
gh run list --repo kkavchenko/news-tracker --workflow=digest.yml --limit 1
```
Take the run ID from the output, then:
```bash
gh run watch <run-id> --repo kkavchenko/news-tracker --exit-status
```
Expected: All steps succeed (checkout, setup-python, install dependencies, generate digest, commit digest.md).

- [ ] **Step 3: Confirm the commit landed on master**

Run: `git -C news-tracker log --oneline -3`
Expected: Top commit is `Update daily digest` authored by `github-actions[bot]`, pushed by the workflow.

- [ ] **Step 4: Pull the change locally and inspect it**

Run: `cd news-tracker && git pull && cat digest.md`
Expected: Content matches (or reasonably updates on) what Task 9 produced locally.

---

### Task 12: Verify the no-op case doesn't break the workflow

**Files:** none (verification only)

- [ ] **Step 1: Trigger the workflow a second time immediately**

Run: `gh workflow run digest.yml --repo kkavchenko/news-tracker`

- [ ] **Step 2: Watch it to completion**

Run the same `gh run list` / `gh run watch` sequence as Task 11, Step 2.
Expected: The job still succeeds, and the "Commit digest.md" step logs `No changes to digest.md, skipping commit.` (since re-running moments later produces an identical file) rather than failing on an empty commit.
