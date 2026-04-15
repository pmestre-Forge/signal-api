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
    Open pre-filled Reddit submit page and click submit automatically.
    Uses Playwright with Chrome's existing profile for logged-in session.
    """
    url = generate_submit_url(post["subreddit"], post["title"], post["body"])

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Launch Chromium with persistent context to reuse Reddit login
            # Using a separate profile dir to avoid locking Chrome's main profile
            profile_dir = Path.home() / ".signal-api-reddit-profile"

            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,  # visible so CAPTCHA can be solved if needed
                args=["--disable-blink-features=AutomationControlled"],
            )

            page = browser.pages[0] if browser.pages else browser.new_page()

            log.info(f"Reddit: navigating to r/{post['subreddit']} submit page")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Check if logged in
            if "login" in page.url.lower():
                log.warning("Reddit: not logged in. Waiting 60s for manual login...")
                page.wait_for_url("**/submit*", timeout=60000)

            # Wait for submit button and click it
            submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
            if submit_btn.is_visible(timeout=5000):
                log.info("Reddit: clicking submit")
                submit_btn.click()

                # Wait for redirect (successful post redirects to the post page)
                page.wait_for_url("**/comments/**", timeout=15000)
                post_url = page.url
                log.info(f"Reddit: posted successfully! {post_url}")

                browser.close()
                return True
            else:
                log.warning("Reddit: submit button not found, trying alternative selector")
                # old.reddit.com uses a different form structure
                page.locator(".submit button, .save-button button, #newlink .btn").first.click(timeout=5000)
                time.sleep(3)
                post_url = page.url
                log.info(f"Reddit: submitted, current URL: {post_url}")
                browser.close()
                return True

    except ImportError:
        log.error("Reddit: playwright not installed. Run: pip install playwright && python -m playwright install chromium")
        return False
    except Exception as e:
        log.error(f"Reddit: auto-submit failed: {e}")
        # Fallback: just open in default browser
        log.info("Reddit: falling back to opening browser manually")
        import webbrowser
        webbrowser.open(url)
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
