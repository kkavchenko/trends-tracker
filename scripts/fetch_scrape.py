"""
For sites with no RSS feed. Uses Playwright to load the page and pull
article title/link pairs via CSS selectors defined per-source in sources_scrape.json.

More fragile than RSS — sites change their HTML. Only add sources here
if RSS genuinely doesn't exist (check /feed, /rss first).
"""
import json
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from supabase import create_client

load_dotenv()

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def load_sources(path="sources_scrape.json"):
    with open(path) as f:
        sources = json.load(f)
    return [s for s in sources if s.get("enabled")]


def scrape_source(page, source):
    page.goto(source["url"], wait_until="domcontentloaded", timeout=30000)
    articles = page.query_selector_all(source["article_selector"])

    count = 0
    for article in articles:
        title_el = article.query_selector(source["title_selector"])
        link_el = article.query_selector(source["link_selector"])
        if not title_el or not link_el:
            continue

        title = title_el.inner_text().strip()
        href = link_el.get_attribute("href")
        if not href:
            continue
        if href.startswith("/"):
            from urllib.parse import urljoin
            href = urljoin(source["url"], href)

        row = {"source": source["name"], "title": title, "url": href}
        try:
            sb.table("articles").upsert(row, on_conflict="url").execute()
            count += 1
        except Exception as e:
            print(f"  ! failed to upsert {href}: {e}")
    return count


def main():
    sources = load_sources()
    if not sources:
        print("No enabled scrape sources. Edit sources_scrape.json to add some.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for source in sources:
            print(f"Scraping {source['name']}...")
            n = scrape_source(page, source)
            print(f"  -> {n} entries processed")
        browser.close()


if __name__ == "__main__":
    main()
