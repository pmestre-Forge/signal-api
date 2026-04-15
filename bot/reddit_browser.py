"""
Reddit auto-poster via Playwright.
Uses Chrome's existing profile so you stay logged in.
No Reddit API keys needed.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from config import API_URL, GITHUB_REPO
from content import REDDIT_POSTS, format_content

try:
    from generate import REDDIT_ROTATION, generate_reddit_post
except ImportError:
    REDDIT_ROTATION = ["algotrading", "LangChain", "autonomous_agents"]
    generate_reddit_post = None

log = logging.getLogger("reddit-browser")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

STATE_FILE = Path(__file__).parent / "state.json"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""

# Chrome user data — Playwright reuses your logged-in session
CHROME_USER_DATA = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_next_reddit_post() -> dict | None:
    """Get the next post — AI generated or static fallback."""
    state = _load_state()
    reddit_idx = state.get("reddit_rotation_idx", 0) % len(REDDIT_ROTATION)
    sub_name = REDDIT_ROTATION[reddit_idx]

    # Try AI generation
    if generate_reddit_post:
        ai_post = generate_reddit_post(sub_name, GITHUB_URL, API_URL)
        if ai_post:
            state["reddit_rotation_idx"] = reddit_idx + 1
            _save_state(state)
            return {
                "subreddit": sub_name,
                "title": ai_post["title"],
                "body": ai_post["body"],
                "source": f"ai:{sub_name}",
            }

    # Fallback to static
    used = state.get("reddit_used", [])
    for post in REDDIT_POSTS:
        if post["angle"] not in used:
            body = format_content(post["body"], GITHUB_REPO, API_URL)
            state.setdefault("reddit_used", []).append(post["angle"])
            state["reddit_rotation_idx"] = reddit_idx + 1
            _save_state(state)
            return {
                "subreddit": post["subreddits"][0],
                "title": post["title"],
                "body": body,
                "source": f"static:{post['angle']}",
            }

    # All used, reset
    state["reddit_used"] = []
    _save_state(state)
    return get_next_reddit_post()


def generate_submit_url(subreddit: str, title: str, body: str) -> str:
    """Generate old.reddit.com submit URL with pre-filled fields."""
    import urllib.parse
    params = urllib.parse.urlencode({
        "selftext": "true",
        "title": title,
        "text": body,
    })
    return f"https://old.reddit.com/r/{subreddit}/submit?{params}"


def auto_submit(post: dict) -> bool:
    """
    Open pre-filled Reddit submit page in user's real browser.
    Reddit blocks Playwright/Selenium, so we use the real browser.
    Also sends Discord notification to alert user to click submit.
    """
    url = generate_submit_url(post["subreddit"], post["title"], post["body"])

    # Open in user's real browser (not blocked by Reddit)
    import webbrowser
    webbrowser.open(url)
    log.info(f"Reddit: opened r/{post['subreddit']} submit page in browser")

    # Alert via Discord so user knows to click submit
    try:
        import httpx
        import os
        webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
        if webhook:
            httpx.post(webhook, json={
                "content": f"**Reddit post ready** -- r/{post['subreddit']}\nTitle: {post['title']}\nThe submit page is open in your browser. Click submit."
            }, timeout=10)
            log.info("Reddit: Discord notification sent")
    except Exception:
        pass

    return True


def open_submit_in_browser() -> bool:
    """Generate the next post and auto-submit via Playwright."""
    post = get_next_reddit_post()
    if not post:
        log.warning("Reddit: no post available")
        return False

    log.info(f"Reddit: posting to r/{post['subreddit']} ({post['source']})")
    success = auto_submit(post)

    # Log it
    state = _load_state()
    state.setdefault("log", []).append({
        "platform": "reddit",
        "angle": post["source"],
        "subreddit": post["subreddit"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save_state(state)
    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reddit Auto-Poster")
    parser.add_argument("--post", action="store_true", help="Auto-submit next post")
    parser.add_argument("--preview", action="store_true", help="Show next post without submitting")
    args = parser.parse_args()

    if args.preview:
        post = get_next_reddit_post()
        if post:
            print(f"Subreddit: r/{post['subreddit']}")
            print(f"Title: {post['title']}")
            print(f"Source: {post['source']}")
            print(f"Body: {post['body'][:300]}...")
        else:
            print("No post available")
    else:
        open_submit_in_browser()
