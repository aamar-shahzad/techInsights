#!/usr/bin/env python3
"""
Build script for Tech Insights news aggregator.
Fetches RSS feeds, filters stories, and generates a static HTML page.
"""

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from jinja2 import Environment, FileSystemLoader

SITE_URL = "https://aamar-shahzad.github.io/techInsights"

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

    top_stories = []
    seen_urls = set()
    category_counts = {}
    max_per_category = 3
    
    all_stories.sort(key=lambda x: x["date"], reverse=True)
    
    for story in all_stories:
        if story["link"] in seen_urls:
            continue
        if story["hours_old"] >= 24:
            continue
            
        cat = story["category"]
        if category_counts.get(cat, 0) >= max_per_category:
            continue
        
        seen_urls.add(story["link"])
        top_stories.append(story)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if len(top_stories) >= TOP_STORIES_COUNT:
            break
    
    top_stories.sort(key=lambda x: x["date"], reverse=True)
    
    print(f"\nTop Stories: {len(top_stories)} from last 24 hours (max {max_per_category} per category)")

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

    generate_sitemap(now)
    generate_archive(env, now, all_stories)
    generate_structured_data(now)


def generate_sitemap(now: datetime):
    """Generate sitemap.xml for SEO."""
    archive_dir = OUTPUT_DIR / "archive"
    
    urls = [
        {"loc": SITE_URL + "/", "changefreq": "daily", "priority": "1.0"},
        {"loc": SITE_URL + "/archive/", "changefreq": "weekly", "priority": "0.8"},
    ]
    
    if archive_dir.exists():
        for week_file in sorted(archive_dir.glob("week-*.html"), reverse=True)[:12]:
            week_name = week_file.stem
            urls.append({
                "loc": f"{SITE_URL}/archive/{week_name}.html",
                "changefreq": "monthly",
                "priority": "0.6"
            })
    
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for url in urls:
        sitemap += "  <url>\n"
        sitemap += f"    <loc>{url['loc']}</loc>\n"
        sitemap += f"    <lastmod>{now.strftime('%Y-%m-%d')}</lastmod>\n"
        sitemap += f"    <changefreq>{url['changefreq']}</changefreq>\n"
        sitemap += f"    <priority>{url['priority']}</priority>\n"
        sitemap += "  </url>\n"
    
    sitemap += "</urlset>"
    
    sitemap_file = OUTPUT_DIR / "sitemap.xml"
    sitemap_file.write_text(sitemap)
    print(f"Generated {sitemap_file}")


def generate_archive(env: Environment, now: datetime, all_stories: list):
    """Generate weekly archive pages."""
    archive_dir = OUTPUT_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    year, week_num, _ = now.isocalendar()
    week_id = f"week-{year}-{week_num:02d}"
    
    week_stories = [s for s in all_stories if s["hours_old"] < 168]
    week_stories.sort(key=lambda x: x["date"], reverse=True)
    
    seen = set()
    unique_stories = []
    for s in week_stories:
        if s["link"] not in seen:
            seen.add(s["link"])
            unique_stories.append(s)
    
    template = env.get_template("archive.html")
    html_content = template.render(
        week_id=week_id,
        week_label=f"Week {week_num}, {year}",
        stories=unique_stories[:50],
        updated_at=now.strftime("%B %d, %Y"),
        year=now.year,
    )
    
    archive_file = archive_dir / f"{week_id}.html"
    archive_file.write_text(html_content)
    print(f"Generated {archive_file}")
    
    weeks = []
    for f in sorted(archive_dir.glob("week-*.html"), reverse=True)[:12]:
        name = f.stem
        parts = name.replace("week-", "").split("-")
        if len(parts) == 2:
            weeks.append({"id": name, "label": f"Week {parts[1]}, {parts[0]}", "file": f"{name}.html"})
    
    index_template = env.get_template("archive_index.html")
    index_content = index_template.render(weeks=weeks, year=now.year)
    (archive_dir / "index.html").write_text(index_content)
    print(f"Generated {archive_dir}/index.html")


def generate_structured_data(now: datetime):
    """Generate JSON-LD structured data for SEO."""
    structured_data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Tech Insights",
        "description": "Daily curated news on AI, developer tools, and the tech industry",
        "url": SITE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{SITE_URL}/?q={{search_term_string}}",
            "query-input": "required name=search_term_string"
        },
        "publisher": {
            "@type": "Organization",
            "name": "Tech Insights",
            "url": SITE_URL
        },
        "dateModified": now.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    json_file = OUTPUT_DIR / "structured-data.json"
    json_file.write_text(json.dumps(structured_data, indent=2))
    print(f"Generated {json_file}")


if __name__ == "__main__":
    build_site()
