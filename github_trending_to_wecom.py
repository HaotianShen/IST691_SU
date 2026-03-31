"""
GitHub Trending → WeCom Robot
Fetches GitHub trending repos and sends them to a WeCom (企业微信) group robot.

Usage:
    pip install requests beautifulsoup4
    python github_trend_to_wecom.py

Configuration:
    Set WECOM_WEBHOOK_URL to your robot webhook URL.
    Optionally set LANGUAGE and TIME_RANGE.
"""
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

WECOM_WEBHOOK_URL = os.environ.get("WECOM_WEBHOOK", "")  # ← read from env

LANGUAGE   = ""        # e.g. "python", "javascript", "" for all languages
TIME_RANGE = "daily"   # "daily" | "weekly" | "monthly"
TOP_N      = 10        # how many repos to include

# ──────────────────────────────────────────────────────────────────────────────


def fetch_trending(language: str = "", since: str = "daily") -> list[dict]:
    """Scrape GitHub Trending page and return a list of repo dicts."""
    url = f"https://github.com/trending/{language}?since={since}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TrendBot/1.0)"}

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")

    repos = []
    for article in articles:
        # Name
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        full_name = h2.get_text(separator="", strip=True).replace("\n", "").replace(" ", "")
        repo_url  = "https://github.com" + h2["href"].strip()

        # Description
        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else "No description"

        # Language
        lang_tag = article.select_one('[itemprop="programmingLanguage"]')
        lang = lang_tag.get_text(strip=True) if lang_tag else "Unknown"

        # Stars total
        star_tags = article.select("a.Link--muted")
        total_stars = star_tags[0].get_text(strip=True) if star_tags else "?"

        # Stars today
        stars_today_tag = article.select_one("span.d-inline-block.float-sm-right")
        stars_today = stars_today_tag.get_text(strip=True) if stars_today_tag else "?"

        repos.append({
            "name":        full_name,
            "url":         repo_url,
            "description": description,
            "language":    lang,
            "stars":       total_stars,
            "stars_today": stars_today,
        })

    return repos


def build_markdown(repos: list[dict], top_n: int, since: str, language: str) -> str:
    """Build a WeCom markdown message."""
    lang_label = language.capitalize() if language else "All Languages"
    since_map  = {"daily": "Today", "weekly": "This Week", "monthly": "This Month"}
    period     = since_map.get(since, since.capitalize())
    date_str   = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"## 🔥 GitHub Trending — {lang_label} ({period})",
        f"> Updated: {date_str}",
        "",
    ]

    for i, r in enumerate(repos[:top_n], 1):
        lines += [
            f"**{i}. [{r['name']}]({r['url']})**",
            f"> {r['description']}",
            f"> 🌐 `{r['language']}`  ⭐ {r['stars']}  📈 +{r['stars_today']}",
            "",
        ]

    return "\n".join(lines)


def send_to_wecom(webhook_url: str, markdown: str) -> None:
    """POST a markdown message to a WeCom robot webhook."""
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": markdown},
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("errcode") != 0:
        raise RuntimeError(f"WeCom API error: {result}")
    print("✅ Message sent successfully!")


def main():
    print(f"Fetching GitHub trending ({TIME_RANGE}, language='{LANGUAGE or 'all'}') ...")
    repos = fetch_trending(language=LANGUAGE, since=TIME_RANGE)
    if not repos:
        print("No trending repos found.")
        return

    markdown = build_markdown(repos, TOP_N, TIME_RANGE, LANGUAGE)
    print("─── Preview ───────────────────────────────")
    print(markdown[:800], "..." if len(markdown) > 800 else "")
    print("───────────────────────────────────────────")

    send_to_wecom(WECOM_WEBHOOK_URL, markdown)


if __name__ == "__main__":
    if not WECOM_WEBHOOK_URL:
        raise ValueError("WECOM_WEBHOOK env variable is not set!")
    main()