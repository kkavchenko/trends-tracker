"""
Print top trending tags over the last N days.
Usage: python scripts/trends.py --days 7
"""
import argparse
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    result = (
        sb.table("articles")
        .select("tags, title, source, url")
        .gte("scraped_at", since)
        .execute()
    )

    counter = Counter()
    for row in result.data:
        for tag in (row.get("tags") or []):
            counter[tag] += 1

    print(f"\nTop tags, last {args.days} days ({len(result.data)} articles):\n")
    for tag, count in counter.most_common(args.top):
        print(f"  {count:>3}  {tag}")


if __name__ == "__main__":
    main()
