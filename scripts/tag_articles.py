"""
Tag any article rows that don't have tags yet, using Claude.
Run this after fetch_rss.py. Safe to re-run — only processes tags is null rows.
"""
import json
import os
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BATCH_SIZE = 20

TAG_PROMPT = """Tag this article with 1-3 short topic tags representing the underlying trend or theme \
(e.g. "AI regulation", "layoffs", "creator economy"). Use lowercase, 1-3 words per tag. \
Respond with ONLY a JSON array of strings, nothing else.

Title: {title}
Summary: {summary}"""


def tag_one(title, summary):
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": TAG_PROMPT.format(title=title, summary=summary or "")}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        tags = json.loads(text)
        if isinstance(tags, list):
            return [str(t) for t in tags]
    except json.JSONDecodeError:
        print(f"  ! couldn't parse tags for '{title}': {text[:100]}")
    return []


def main():
    result = (
        sb.table("articles")
        .select("id, title, summary")
        .is_("tags", "null")
        .limit(BATCH_SIZE)
        .execute()
    )
    rows = result.data
    if not rows:
        print("Nothing to tag.")
        return

    print(f"Tagging {len(rows)} articles...")
    for row in rows:
        tags = tag_one(row["title"], row.get("summary", ""))
        sb.table("articles").update({
            "tags": tags,
            "tagged_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row["id"]).execute()
        print(f"  {row['title'][:60]:<60} -> {tags}")

    print("Done. Re-run this script if there were more than BATCH_SIZE rows pending.")


if __name__ == "__main__":
    main()
