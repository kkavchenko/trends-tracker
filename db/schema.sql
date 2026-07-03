-- Enable pgvector if you want embeddings-based clustering later (optional, can skip for now)
-- create extension if not exists vector;

create table if not exists articles (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  title text not null,
  url text unique not null,
  published_at timestamptz,
  summary text,
  raw_text text,
  tags text[],
  -- embedding vector(1536), -- uncomment if using embeddings later
  scraped_at timestamptz default now(),
  tagged_at timestamptz
);

create index if not exists idx_articles_scraped_at on articles (scraped_at);
create index if not exists idx_articles_tags on articles using gin (tags);
