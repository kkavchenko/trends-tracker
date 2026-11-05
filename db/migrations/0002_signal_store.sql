-- Phase 1 of the signal system (see kkavchenko/newsletter-digests BUILD_LOG.md
-- for the audit and scoping that led here). Adds the one store that the
-- aggregator, the Off Brief bot and the morning brief will all read/write
-- against eventually. Additive only: `articles` is untouched, so this is
-- fully reversible by dropping the tables below.
--
-- One deviation from the plan's draft schema: `items` gets an `origin`
-- column that the draft didn't have. The draft's `source` is a category
-- enum (rss/newsletter/telegram_link/...), but `articles.source` today
-- holds the feed/site name ("Wired", "TechCrunch"...). Reusing `source`
-- for both would silently lose which outlet each item came from -- so
-- `origin` carries the old per-source name and `source` keeps the enum.
--
-- Run this in the Supabase SQL editor (same as db/schema.sql originally).

create extension if not exists vector;

create table items (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('rss','newsletter','telegram_link','telegram_note','voice','screenshot')),
  origin text,                 -- feed/site name, e.g. "Wired" (was articles.source)
  url text,
  title text,
  raw_text text,
  summary text,
  user_note text,              -- what Katya typed alongside a save
  is_ob boolean default false, -- flagged for Off Brief
  is_saved boolean default false, -- Katya's own save vs. feed item
  published_at timestamptz,
  captured_at timestamptz default now(),
  embedding vector(1024)       -- match the embedding model chosen in Phase 3
);

-- Dedup for feed-sourced items (rss/newsletter always have a url; Telegram
-- notes and voice captures may not, so this only constrains non-null urls).
-- Needed for fetch_rss.py / fetch_scrape.py's upsert(on_conflict="url").
create unique index items_url_unique on items (url) where url is not null;

create table themes (
  id uuid primary key default gen_random_uuid(),
  label text unique not null,
  description text,
  status text default 'active' check (status in ('active','proposed','merged')),
  merged_into uuid references themes(id)
);

create table item_themes (
  item_id uuid references items(id) on delete cascade,
  theme_id uuid references themes(id),
  confidence real,
  primary key (item_id, theme_id)
);

create table theme_weeks (
  theme_id uuid references themes(id),
  week date,
  feed_count int,
  saved_count int,
  momentum real,  -- change vs. trailing 4 weeks
  primary key (theme_id, week)
);

create table briefs (
  id uuid primary key default gen_random_uuid(),
  kind text check (kind in ('morning','off_brief')),
  for_date date,
  content_md text,
  audio_url text,
  created_at timestamptz default now()
);

create table reactions (
  item_id uuid references items(id) on delete cascade,
  brief_id uuid references briefs(id),
  kind text check (kind in ('up','down','save')),
  at timestamptz default now()
);
