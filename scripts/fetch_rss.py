"""
Pull all configured RSS feeds and upsert new articles into Supabase.
Dedup is handled by the `url` unique constraint — safe to re-run anytime.
"""
import json
import os
from datetime import datetime, timezone

import feedparser
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def load_sources(path="sources.json"):
    with open(path) as f:
        return json.load(f)


def parse_published(entry):
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    return None


def fetch_source(source):
    feed = feedparser.parse(source["url"])
    if feed.bozo and not feed.entries:
        print(f"  ! failed to parse {source['name']}: {feed.bozo_exception}")
        return 0

    count = 0
    for entry in feed.entries:
        row = {
            "source": source["name"],
            "title": entry.get("title", "(untitled)"),
            "url": entry.get("link"),
            "published_at": parse_published(entry),
            "summary": entry.get("summary", "")[:2000],  # keep it bounded
        }
        if not row["url"]:
            continue
        try:
            sb.table("articles").upsert(row, on_conflict="url").execute()
            count += 1
        except Exception as e:
            print(f"  ! failed to upsert {row['url']}: {e}")
    return count


def main():
    sources = load_sources()
    total = 0
    for source in sources:
        print(f"Fetching {source['name']}...")
        n = fetch_source(source)
        print(f"  -> {n} entries processed")
        total += n
    print(f"Done. {total} entries processed across {len(sources)} sources.")


if __name__ == "__main__":
    main()
