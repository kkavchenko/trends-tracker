# news-tracker

Scrapes/pulls RSS from a configurable list of news + newsletter sources, stores articles in Supabase, tags each with Claude, and lets you query trends over time.

## Setup

1. **Create a Supabase project** (free tier is fine) at supabase.com.

2. **Run the schema** in the Supabase SQL editor:
   ```
   cat db/schema.sql
   ```
   paste it into the SQL editor and run.

3. **Install deps**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Set environment variables** — copy `.env.example` to `.env` and fill in:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (service role key, not anon — this runs server-side)
   - `ANTHROPIC_API_KEY`

5. **Edit `sources.json`** — add your RSS feeds. Each entry needs `name` and `url`. For sites without RSS, add them to `sources_scrape.json` instead (uses Playwright, needs selectors — see comments in that file).

6. **Test the pipeline on a few sources first**
   ```bash
   python scripts/fetch_rss.py
   python scripts/tag_articles.py
   ```
   Check Supabase's table editor to confirm rows landed and got tagged before scaling up your source list.

7. **Automate it** — the GitHub Actions workflow in `.github/workflows/fetch.yml` runs every 6 hours. Add your three secrets (`SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`) under repo Settings → Secrets → Actions, and push. That's it — no server to babysit.

## Querying trends

```bash
python scripts/trends.py --days 7
```

or query Supabase directly:
```sql
select unnest(tags) as tag, count(*)
from articles
where scraped_at > now() - interval '7 days'
group by tag
order by count(*) desc;
```

## Adding scrape-only sources (no RSS)

`sources_scrape.json` entries need CSS selectors for title/link since there's no feed structure to lean on. This is more fragile — sites change their HTML and you'll need to update selectors occasionally. Prefer RSS wherever it exists.
