"""
One-time backfill: copy every row in `articles` into `items`.

Run this once, after applying db/migrations/0002_signal_store.sql, and
before pointing fetch_rss.py / fetch_scrape.py at `items`. Safe to re-run —
skips any url already present in `items`.

Deliberately dropped on migration (not carried over):
  - `tags` — free-form, tagged by the old tag_articles.py. The signal
    system uses a controlled theme vocabulary built fresh in Phase 3, so
    carrying these over would just seed `themes` with noise.
  - `embedding` — stays null; Phase 3 backfills it.

Everything else maps straight across. All backfilled rows get
source='rss', is_saved=false, is_ob=false — none of this is a Katya save.

Usage:
  python scripts/migrate_articles_to_items.py
  python scripts/migrate_articles_to_items.py --dry-run
"""
import argparse
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

BATCH_SIZE = 500


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="count only, write nothing")
    args = parser.parse_args()

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    existing = sb.table("items").select("url").execute().data
    already = {row["url"] for row in existing if row["url"]}
    print(f"{len(already)} url(s) already in items.")

    migrated = 0
    skipped = 0
    offset = 0
    while True:
        batch = (
            sb.table("articles")
            .select("url, title, source, raw_text, summary, published_at, scraped_at")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
            .data
        )
        if not batch:
            break

        rows = []
        for row in batch:
            if row["url"] in already:
                skipped += 1
                continue
            rows.append({
                "source": "rss",
                "origin": row.get("source"),
                "url": row["url"],
                "title": row["title"],
                "raw_text": row.get("raw_text"),
                "summary": row.get("summary"),
                "published_at": row.get("published_at"),
                "captured_at": row.get("scraped_at"),
                "is_saved": False,
                "is_ob": False,
            })
            already.add(row["url"])

        if rows and not args.dry_run:
            sb.table("items").insert(rows).execute()
        migrated += len(rows)
        print(f"  batch at offset {offset}: {len(rows)} to migrate, {len(batch) - len(rows)} skipped")
        offset += BATCH_SIZE

    verb = "would migrate" if args.dry_run else "migrated"
    print(f"Done. {verb} {migrated} row(s), skipped {skipped} already present.")


if __name__ == "__main__":
    main()
