# Trend Digest — Design

## Purpose

Add a daily, human-readable digest that summarizes trending topics from the
`articles` table, so trends can be followed as they emerge and grow over
time — not just as a raw tag-count snapshot.

## Delivery & frequency

- A single markdown file, `digest.md`, lives at the repo root.
- It is regenerated once a day and committed back to `master` by a
  dedicated GitHub Actions workflow.
- The file is overwritten each run (no dated archive). This is safe because
  the underlying source data (`articles.tags`, `articles.scraped_at`) is
  never deleted — every run recomputes trend direction from that permanent
  history, so nothing is actually lost by overwriting the rendered file.

## Data flow (`scripts/digest.py`)

1. Query Supabase once for all rows from the last 14 days:
   `select tags, title, url, source, scraped_at from articles where scraped_at > now() - interval '14 days'`.
2. Split the rows in Python into two windows using `scraped_at`:
   - **This week**: last 7 days.
   - **Last week**: 7–14 days ago.
3. Count tag occurrences independently in each window (`Counter`, same
   pattern as `trends.py`).
4. Rank tags by **this week's** count, descending. Take the top 10.
5. For each of those top 10 tags, compute a direction indicator by
   comparing this week's count to last week's count for that tag:
   - `↑` — this week's count is higher.
   - `↓` — this week's count is lower.
   - `→` — counts are equal (and last week's count was > 0).
   - `🆕` — tag did not appear at all last week.
6. For each top tag, select up to 2 example articles from this week's
   window (most recent by `scraped_at`), deduplicated by `url`.
7. Render everything to markdown and overwrite `digest.md`.

## Output format

```markdown
# News Tracker Digest — 2026-07-10

## Top Trends (this week vs. last week)

### 1. AI regulation — 12 articles this week (↑ from 7 last week)
- [EU Finalizes AI Act Enforcement Rules](https://...) — Wired AI
- [Senate Hearing on Model Safety](https://...) — Wired AI

### 2. Creator economy — 8 articles this week (→ steady, was 8 last week)
- [Substack's New Ad Model](https://...) — BOM

### 3. Nostalgia economy — 3 articles this week (🆕 new this week)
- ["Nostalgia Is Not a Strategy"](https://...) — Paul Graham
```

If there are zero articles in the last 7 days, `digest.py` writes a simple
placeholder instead of an empty or malformed file:

```markdown
# News Tracker Digest — 2026-07-10

No new articles in the last 7 days.
```

## Workflow (`.github/workflows/digest.yml`)

- Separate file from `fetch.yml` — different schedule and concern.
- Triggers: `schedule: cron: '0 8 * * *'` (daily, 8am UTC) +
  `workflow_dispatch` for manual runs.
- `permissions: contents: write` set explicitly (default token is often
  read-only).
- Steps: checkout → setup Python 3.11 → `pip install supabase
  python-dotenv` (only what `digest.py` needs — no Playwright/Anthropic
  required for a read-only report) → run `python scripts/digest.py` →
  commit + push `digest.md` using a bot identity
  (`github-actions[bot]` / `github-actions[bot]@users.noreply.github.com`).
- The commit step is guarded so a day with no changes to `digest.md`
  doesn't fail the job (skip commit/push if `git diff --quiet` on the
  file).
- Reuses existing `SUPABASE_URL` / `SUPABASE_KEY` repo secrets. No new
  secrets required.

## Error handling

- No schema changes needed — `tags` and `scraped_at` already exist on
  `articles`.
- If the Supabase query fails, `digest.py` errors out normally (same
  behavior as `trends.py` today) — no added retry logic, consistent with
  the rest of the codebase's existing error-handling style.
- Zero-data case (no articles in 7 days) produces a valid placeholder
  file rather than crashing or writing an empty file.

## Testing / validation plan

1. Run `scripts/digest.py` locally against the real Supabase project and
   manually confirm the rendered `digest.md` content and formatting.
2. Push `digest.yml` and manually trigger it via `workflow_dispatch`
   (`gh workflow run digest.yml`), confirming: the job succeeds, a commit
   appears on `master` updating `digest.md`, and the file content matches
   what the local run produced.
3. Verify the no-op case: run the workflow a second time with no new
   articles since the last run, confirming the job succeeds without
   producing an empty/no-op commit.
