# Tech Insights

A minimal, serverless news aggregator for AI, developer tools, and tech industry news. Hosted on GitHub Pages with daily automatic updates via GitHub Actions.

## Features

- **No server required** - Pure static HTML generated from RSS feeds
- **Daily updates** - GitHub Actions fetches fresh stories every morning at 6 AM UTC
- **Three categories** - AI, Developer Tools, and Tech Industry news
- **Clean design** - Responsive, dark/light mode support
- **Zero dependencies** - No JavaScript frameworks, just vanilla HTML/CSS

## RSS Sources

### AI
- TechCrunch AI
- MIT Technology Review
- Wired AI

### Developer Tools
- Dev.to
- GitHub Blog
- Hacker News (front page)

### Tech Industry
- The Verge
- Ars Technica

## Setup

### 1. Fork or Clone

```bash
git clone https://github.com/YOUR_USERNAME/techInsights.git
cd techInsights
```

### 2. Enable GitHub Pages

1. Go to your repository **Settings**
2. Navigate to **Pages** (under "Code and automation")
3. Under "Source", select **Deploy from a branch**
4. Choose branch: `main`, folder: `/docs`
5. Click **Save**

### 3. Trigger First Build

Either wait for the daily cron job, or manually trigger:

1. Go to **Actions** tab
2. Select "Build News Site"
3. Click **Run workflow**

Your site will be live at `https://YOUR_USERNAME.github.io/techInsights/`

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Build the site
python scripts/build.py

# Preview (optional)
open docs/index.html
```

## Customization

### Add/Remove Feeds

Edit the `FEEDS` dictionary in `scripts/build.py`:

```python
FEEDS = {
    "ai": [
        ("Source Name", "https://example.com/feed.xml"),
    ],
    # ...
}
```

### Change Update Schedule

Edit `.github/workflows/build.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'  # 6 AM UTC daily
```

## License

MIT
