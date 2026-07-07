"""
Generate a daily trend digest comparing this week's tag counts to last
week's, sourced entirely from the articles table's existing history
(no separate archive file is kept).
"""

import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from dateutil.parser import isoparse
from dotenv import load_dotenv


def parse_timestamp(value):
    """Parse an ISO-8601 timestamp string, tolerating the variable-precision
    fractional-seconds component and both Z/offset suffix styles that
    Supabase/Postgres can produce.
    """
    return isoparse(value)


def split_windows(rows, now):
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)
    this_week = []
    last_week = []
    for row in rows:
        scraped_at = parse_timestamp(row["scraped_at"])
        if scraped_at >= this_week_start:
            this_week.append(row)
        elif scraped_at >= last_week_start:
            last_week.append(row)
    return this_week, last_week


def count_tags(rows):
    counter = Counter()
    for row in rows:
        for tag in (row.get("tags") or []):
            counter[tag] += 1
    return counter


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


def pick_examples(this_week_rows, tag, limit=2):
    matches = [r for r in this_week_rows if tag in (r.get("tags") or [])]
    matches.sort(key=lambda r: parse_timestamp(r["scraped_at"]), reverse=True)
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


def build_digest_entries(this_week_rows, last_week_rows, top_n=10, examples_per_tag=2):
    this_counts = count_tags(this_week_rows)
    last_counts = count_tags(last_week_rows)
    ranked = rank_tags(this_counts, last_counts, top_n=top_n)
    for entry in ranked:
        entry["examples"] = pick_examples(this_week_rows, entry["tag"], limit=examples_per_tag)
    return ranked


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
