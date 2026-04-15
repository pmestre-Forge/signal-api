"""
Auto-advertiser. Uses Forge's existing publishers for Twitter/X, Reddit, Dev.to, Discord.
Rotates content angles and tracks what was posted to avoid spam.
"""

import json
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import API_URL, DISCORD_WEBHOOK_URL, FORGE_ROOT, GITHUB_REPO, STATE_FILE
from content import (
    DEVTO_ARTICLES,
    DISCORD_POSTS,
    REDDIT_POSTS,
    TWITTER_THREADS,
    format_content,
)

# Add Forge publishers to path
sys.path.insert(0, str(FORGE_ROOT / "twitter"))
sys.path.insert(0, str(FORGE_ROOT / "devto"))

log = logging.getLogger("signal-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"twitter_used": [], "reddit_used": [], "devto_used": [], "discord_used": [], "log": []}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _pick_unused(items: list[dict], used: list[str]) -> dict | None:
    available = [i for i in items if i["angle"] not in used]
    if not available:
        return None
    return available[0]


def _log_post(state: dict, platform: str, angle: str, url: str = "") -> None:
    state["log"].append({
        "platform": platform,
        "angle": angle,
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Twitter/X — via Forge TwitterPublisher
# ---------------------------------------------------------------------------
def post_twitter(state: dict) -> bool:
    thread_data = _pick_unused(TWITTER_THREADS, state["twitter_used"])
    if not thread_data:
        log.info("Twitter: all angles used, resetting rotation")
        state["twitter_used"] = []
        thread_data = _pick_unused(TWITTER_THREADS, [])

    if not thread_data:
        return False

    try:
        from publisher import TwitterPublisher

        twitter = TwitterPublisher(
            credentials_path=str(FORGE_ROOT / "credentials" / "twitter.json")
        )

        tweets = [format_content(t, GITHUB_REPO, API_URL) for t in thread_data["tweets"]]

        # Enforce 280 char limit per tweet
        for i, t in enumerate(tweets):
            if len(t) > 280:
                tweets[i] = t[:277] + "..."

        results = twitter.post_thread(tweets)
        first_id = results[0].get("data", {}).get("id", "")
        url = f"https://x.com/PedroForge/status/{first_id}" if first_id else ""

        log.info(f"Twitter: posted thread (angle={thread_data['angle']}) {url}")
        state["twitter_used"].append(thread_data["angle"])
        _log_post(state, "twitter", thread_data["angle"], url)
        return True

    except Exception as e:
        log.error(f"Twitter post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Dev.to — via Forge DevtoPublisher
# ---------------------------------------------------------------------------
def post_devto(state: dict) -> bool:
    article_data = _pick_unused(DEVTO_ARTICLES, state["devto_used"])
    if not article_data:
        log.info("Dev.to: all angles used, resetting rotation")
        state["devto_used"] = []
        article_data = _pick_unused(DEVTO_ARTICLES, [])

    if not article_data:
        return False

    try:
        from publisher import DevtoPublisher

        # Temporarily adjust sys.path for devto publisher
        devto_path = str(FORGE_ROOT / "devto")
        if devto_path not in sys.path:
            sys.path.insert(0, devto_path)

        devto = DevtoPublisher(
            credentials_path=str(FORGE_ROOT / "credentials" / "devto.json")
        )

        body = format_content(article_data["body"], GITHUB_REPO, API_URL)

        result = devto.publish_article(
            title=article_data["title"],
            body_markdown=body,
            tags=article_data["tags"],
            published=True,
        )

        url = result.get("url", "")
        log.info(f"Dev.to: published article (angle={article_data['angle']}) {url}")
        state["devto_used"].append(article_data["angle"])
        _log_post(state, "devto", article_data["angle"], url)
        return True

    except Exception as e:
        log.error(f"Dev.to post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Reddit — via Forge reddit_autoposter's PRAW setup
# ---------------------------------------------------------------------------
def post_reddit(state: dict) -> bool:
    post_data = _pick_unused(REDDIT_POSTS, state["reddit_used"])
    if not post_data:
        log.info("Reddit: all angles used, resetting rotation")
        state["reddit_used"] = []
        post_data = _pick_unused(REDDIT_POSTS, [])

    if not post_data:
        return False

    # Reddit needs its own .env in Forge
    reddit_env = FORGE_ROOT / "reddit" / ".env"
    if not reddit_env.exists():
        log.warning("Reddit: no .env found at Forge/forge-distro/reddit/.env — skipping")
        return False

    try:
        import os
        from dotenv import load_dotenv
        import praw

        load_dotenv(reddit_env)

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        username = os.getenv("REDDIT_USERNAME")
        password = os.getenv("REDDIT_PASSWORD")

        if not all([client_id, client_secret, username, password]):
            log.warning("Reddit: credentials incomplete in .env — skipping")
            return False

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=f"SignalAPIBot/1.0 (by /u/{username})",
        )

        body = format_content(post_data["body"], GITHUB_REPO, API_URL)
        posted = False

        for sub_name in post_data["subreddits"]:
            try:
                submission = reddit.subreddit(sub_name).submit(
                    title=post_data["title"],
                    selftext=body,
                )
                url = f"https://reddit.com{submission.permalink}"
                log.info(f"Reddit: posted to r/{sub_name} {url}")
                _log_post(state, "reddit", f"{post_data['angle']}:{sub_name}", url)
                posted = True
            except Exception as e:
                log.error(f"Reddit: failed to post to r/{sub_name}: {e}")

        if posted:
            state["reddit_used"].append(post_data["angle"])
        return posted

    except Exception as e:
        log.error(f"Reddit post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Discord — webhook
# ---------------------------------------------------------------------------
def post_discord(state: dict) -> bool:
    post_data = _pick_unused(DISCORD_POSTS, state["discord_used"])
    if not post_data:
        state["discord_used"] = []
        post_data = _pick_unused(DISCORD_POSTS, [])

    if not post_data or not DISCORD_WEBHOOK_URL:
        return False

    content = format_content(post_data["content"], GITHUB_REPO, API_URL)

    try:
        r = httpx.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
        if r.status_code in (200, 204):
            log.info(f"Discord: posted (angle={post_data['angle']})")
            state["discord_used"].append(post_data["angle"])
            _log_post(state, "discord", post_data["angle"])
            return True
        else:
            log.error(f"Discord: webhook returned {r.status_code}")
    except Exception as e:
        log.error(f"Discord: post failed: {e}")

    return False


# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------
def run_ads() -> None:
    """Run one advertising cycle across all platforms."""
    state = _load_state()
    now = datetime.now(timezone.utc).isoformat()

    log.info(f"[{now}] Ad cycle starting")
    log.info(f"  Used angles — Twitter: {state['twitter_used']}, Reddit: {state['reddit_used']}, "
             f"Dev.to: {state['devto_used']}, Discord: {state['discord_used']}")

    post_twitter(state)
    post_devto(state)
    post_reddit(state)
    post_discord(state)

    _save_state(state)
    log.info("Ad cycle complete")


if __name__ == "__main__":
    run_ads()
