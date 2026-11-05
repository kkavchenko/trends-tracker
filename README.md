# news-tracker

Scrapes/pulls RSS from a configurable list of news + newsletter sources and stores items in Supabase. This is the ingestion half of Katya's signal system (see `kkavchenko/newsletter-digests` for the morning-brief side and `BUILD_LOG.md`-style history of how this got scoped).

## Setup

1. **Create a Supabase project** (free tier is fine) at supabase.com.

2. **Run the schema** in the Supabase SQL editor, in order:
   ```
   cat db/schema.sql                       # legacy `articles` table, kept for history
   cat db/migrations/0002_signal_store.sql  # the `items` table this now writes to, plus themes/briefs/reactions for later phases
   ```
   paste each into the SQL editor and run.

3. **Install deps**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Set environment variables** — copy `.env.example` to `.env` and fill in:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (service role key, not anon — this runs server-side)
   - `ANTHROPIC_API_KEY` (unused by the current pipeline; kept for later phases' tagging/enrichment)

5. **Edit `sources.json`** — add your RSS feeds. Each entry needs `name` and `url`. For sites without RSS, add them to `sources_scrape.json` instead (uses Playwright, needs selectors — see comments in that file).

6. **One-time only, after step 2**: backfill the old `articles` rows into `items`:
   ```bash
   python scripts/migrate_articles_to_items.py
   ```
   Safe to re-run — skips urls already present in `items`.

7. **Test the pipeline on a few sources first**
   ```bash
   python scripts/fetch_rss.py
   ```
   Check Supabase's table editor to confirm rows landed in `items` before scaling up your source list.

8. **Automate it** — the GitHub Actions workflow in `.github/workflows/fetch.yml` runs every 6 hours. Add your secrets (`SUPABASE_URL`, `SUPABASE_KEY`) under repo Settings → Secrets → Actions, and push. That's it — no server to babysit.

## Status (as of Phase 1 of the signal system)

- `fetch_rss.py` / `fetch_scrape.py` write to `items`, not `articles`. `articles` is kept, untouched, as history/rollback.
- Claude-based tagging (`tag_articles.py`) is removed — it tagged with free-form tags, not the controlled theme vocabulary the signal system uses. Theme tagging is rebuilt from scratch against `items` in a later phase.
- The daily `digest.yml` workflow (tag-trend digest off `articles.tags`) is retired — unused, so it's gone rather than left to go stale. `scripts/digest.py`, `scripts/trends.py` and their tests are still here if that logic is ever worth reviving against `items`, but nothing runs them automatically anymore.

## Adding scrape-only sources (no RSS)

`sources_scrape.json` entries need CSS selectors for title/link since there's no feed structure to lean on. This is more fragile — sites change their HTML and you'll need to update selectors occasionally. Prefer RSS wherever it exists.
