#!/usr/bin/env python3
"""
Build script for Tech Insights news aggregator.
Fetches RSS feeds, filters stories, and generates a static HTML page.
"""

import html
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from jinja2 import Environment, FileSystemLoader

FEEDS = {
    "ai": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
        ("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss"),
        ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
        ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
        ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ],
    "devtools": [
        ("Dev.to", "https://dev.to/feed/"),
        ("GitHub Blog", "https://github.blog/feed/"),
        ("Hacker News", "https://hnrss.org/frontpage"),
    ],
    "tech": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ],
    "startups": [
        ("Y Combinator", "https://www.ycombinator.com/blog/rss/"),
        ("a16z", "https://a16z.com/feed/"),
        ("First Round Review", "https://review.firstround.com/feed.xml"),
    ],
    "security": [
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
        ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
        ("Schneier on Security", "https://www.schneier.com/feed/"),
    ],
}

CATEGORY_LABELS = {
    "ai": "AI",
    "devtools": "Developer Tools",
    "tech": "Tech Industry",
    "startups": "Startups & VC",
    "security": "Security",
}

MAX_STORIES_PER_CATEGORY = 10
MAX_DESCRIPTION_LENGTH = 200
TOP_STORIES_COUNT = 10

PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "docs"


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rsplit(" ", 1)[0] + "..."


def time_ago(dt: datetime) -> str:
    """Convert datetime to human-readable 'time ago' format."""
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    seconds = diff.total_seconds()
    if seconds < 0:
        return "just now"
    
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24
    
    if seconds < 60:
        return "just now"
    elif minutes < 60:
        m = int(minutes)
        return f"{m} min ago" if m == 1 else f"{m} mins ago"
    elif hours < 24:
        h = int(hours)
        return f"{h} hour ago" if h == 1 else f"{h} hours ago"
    elif days < 7:
        d = int(days)
        return f"{d} day ago" if d == 1 else f"{d} days ago"
    else:
        return dt.strftime("%b %d, %Y")


def parse_date(entry) -> datetime:
    """Extract published date from feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_feed(source_name: str, url: str) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    stories = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link = entry.get("link", "")
            if not link:
                continue

            title = entry.get("title", "Untitled")
            description = strip_html(entry.get("summary", entry.get("description", "")))
            description = truncate(description, MAX_DESCRIPTION_LENGTH)
            pub_date = parse_date(entry)

            now = datetime.now(timezone.utc)
            hours_old = (now - pub_date).total_seconds() / 3600
            
            stories.append({
                "title": title,
                "link": link,
                "description": description,
                "source": source_name,
                "date": pub_date,
                "date_str": pub_date.strftime("%b %d, %Y"),
                "time_ago": time_ago(pub_date),
                "is_new": hours_old < 6,
                "hours_old": hours_old,
            })
    except Exception as e:
        print(f"Error fetching {source_name} ({url}): {e}")

    return stories


def fetch_category(category: str) -> list[dict]:
    """Fetch all feeds for a category and deduplicate."""
    all_stories = []
    seen_urls = set()

    for source_name, url in FEEDS[category]:
        print(f"  Fetching {source_name}...")
        stories = fetch_feed(source_name, url)
        for story in stories:
            if story["link"] not in seen_urls:
                seen_urls.add(story["link"])
                all_stories.append(story)

    all_stories.sort(key=lambda x: x["date"], reverse=True)
    return all_stories[:MAX_STORIES_PER_CATEGORY]


def build_site():
    """Main build function."""
    print("Building Tech Insights...")

    categories_data = []
    all_stories = []
    
    for category_id in ["ai", "devtools", "tech", "startups", "security"]:
        print(f"\nCategory: {CATEGORY_LABELS[category_id]}")
        stories = fetch_category(category_id)
        print(f"  Found {len(stories)} stories")
        
        for story in stories:
            story["category"] = category_id
            story["category_label"] = CATEGORY_LABELS[category_id]
        
        all_stories.extend(stories)
        categories_data.append({
            "id": category_id,
            "label": CATEGORY_LABELS[category_id],
            "stories": stories,
        })

    all_stories.sort(key=lambda x: x["date"], reverse=True)
    seen_urls = set()
    top_stories = []
    for story in all_stories:
        if story["link"] not in seen_urls and story["hours_old"] < 24:
            seen_urls.add(story["link"])
            top_stories.append(story)
            if len(top_stories) >= TOP_STORIES_COUNT:
                break
    
    print(f"\nTop Stories: {len(top_stories)} from last 24 hours")

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("page.html")

    now = datetime.now(timezone.utc)
    html_content = template.render(
        top_stories=top_stories,
        categories=categories_data,
        updated_at=now.strftime("%B %d, %Y at %H:%M UTC"),
        year=now.year,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "index.html"
    output_file.write_text(html_content)
    print(f"\nGenerated {output_file}")


if __name__ == "__main__":
    build_site()
