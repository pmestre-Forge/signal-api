"""
Reddit browser poster. Posts to Reddit via old.reddit.com submit page.
No API keys needed — uses logged-in browser session.

Usage:
    python reddit_browser.py --subreddit algotrading --title "My title" --body "My body"
    python reddit_browser.py --test  # dry run, opens submit page but doesn't post
"""

import argparse
import json
import logging
import random
import sys
import time
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


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_next_reddit_post() -> dict | None:
    """Get the next post to make — AI generated or static fallback."""
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


def generate_instructions(post: dict) -> str:
    """Generate step-by-step browser automation instructions for Claude."""
    url = generate_submit_url(post["subreddit"], post["title"], post["body"])
    return f"""REDDIT POST INSTRUCTIONS:

1. Navigate to: {url}
2. If not logged in: user needs to log in first
3. Verify the title and body are pre-filled correctly
4. Click the "submit" button
5. Wait for redirect to confirm post was created
6. Log the result

Subreddit: r/{post['subreddit']}
Title: {post['title']}
Body length: {len(post['body'])} chars
Source: {post['source']}
"""


def open_submit_in_browser() -> bool:
    """Generate the next post and open the submit URL in the default browser."""
    post = get_next_reddit_post()
    if not post:
        log.warning("Reddit: no post available")
        return False

    url = generate_submit_url(post["subreddit"], post["title"], post["body"])
    log.info(f"Reddit: opening r/{post['subreddit']} submit page ({post['source']})")

    import webbrowser
    webbrowser.open(url)

    # Log it
    state = _load_state()
    state.setdefault("log", []).append({
        "platform": "reddit-browser",
        "angle": post["source"],
        "subreddit": post["subreddit"],
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    })
    _save_state(state)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reddit Browser Poster")
    parser.add_argument("--next", action="store_true", help="Show next post to make")
    parser.add_argument("--url", action="store_true", help="Generate submit URL for next post")
    parser.add_argument("--instructions", action="store_true", help="Generate browser automation instructions")
    parser.add_argument("--subreddit", type=str, help="Override subreddit")
    parser.add_argument("--title", type=str, help="Override title")
    parser.add_argument("--body", type=str, help="Override body")
    args = parser.parse_args()

    if args.subreddit and args.title and args.body:
        post = {
            "subreddit": args.subreddit,
            "title": args.title,
            "body": args.body,
            "source": "manual",
        }
    else:
        post = get_next_reddit_post()

    if not post:
        print("No post available")
        sys.exit(1)

    if args.url:
        print(generate_submit_url(post["subreddit"], post["title"], post["body"]))
    elif args.instructions:
        print(generate_instructions(post))
    else:
        print(f"Subreddit: r/{post['subreddit']}")
        print(f"Title: {post['title']}")
        print(f"Source: {post['source']}")
        print(f"Body ({len(post['body'])} chars):")
        print(post['body'][:500])
        print(f"\nSubmit URL:")
        print(generate_submit_url(post["subreddit"], post["title"], post["body"]))
