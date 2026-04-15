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
    GITHUB_AWESOME_PRS,
    REDDIT_POSTS,
    TWITTER_THREADS,
    format_content,
)
from generate import (
    DEVTO_ANGLES,
    REDDIT_ROTATION,
    TWITTER_ANGLES,
    generate_devto_article,
    generate_reddit_post,
    generate_twitter_thread,
)

# Forge publisher paths — loaded on demand to avoid import conflicts

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
    github_url = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("twitter_pub", str(FORGE_ROOT / "twitter" / "publisher.py"))
        twitter_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(twitter_mod)
        TwitterPublisher = twitter_mod.TwitterPublisher

        twitter = TwitterPublisher(
            credentials_path=str(FORGE_ROOT / "credentials" / "twitter.json")
        )

        # Try AI-generated content first
        ai_angle_idx = state.get("twitter_ai_idx", 0) % len(TWITTER_ANGLES)
        angle = TWITTER_ANGLES[ai_angle_idx]
        tweets = generate_twitter_thread(angle, github_url, API_URL)

        if tweets:
            log.info(f"Twitter: using AI-generated thread (angle: {angle[:50]})")
            state["twitter_ai_idx"] = ai_angle_idx + 1
            source = f"ai:{angle[:30]}"
        else:
            # Fallback to static content
            thread_data = _pick_unused(TWITTER_THREADS, state["twitter_used"])
            if not thread_data:
                state["twitter_used"] = []
                thread_data = _pick_unused(TWITTER_THREADS, [])
            if not thread_data:
                return False

            tweets = [format_content(t, GITHUB_REPO, API_URL) for t in thread_data["tweets"]]
            state["twitter_used"].append(thread_data["angle"])
            source = f"static:{thread_data['angle']}"

        # Enforce 280 char limit
        for i, t in enumerate(tweets):
            if len(t) > 280:
                tweets[i] = t[:277] + "..."

        results = twitter.post_thread(tweets)
        first_id = results[0].get("data", {}).get("id", "")
        url = f"https://x.com/PedroForge/status/{first_id}" if first_id else ""

        log.info(f"Twitter: posted thread ({source}) {url}")
        _log_post(state, "twitter", source, url)
        return True

    except Exception as e:
        log.error(f"Twitter post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Dev.to — via Forge DevtoPublisher
# ---------------------------------------------------------------------------
def post_devto(state: dict) -> bool:
    github_url = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("devto_pub", str(FORGE_ROOT / "devto" / "publisher.py"))
        devto_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(devto_mod)
        DevtoPublisher = devto_mod.DevtoPublisher

        devto = DevtoPublisher(
            credentials_path=str(FORGE_ROOT / "credentials" / "devto.json")
        )

        # Try AI-generated article first
        ai_angle_idx = state.get("devto_ai_idx", 0) % len(DEVTO_ANGLES)
        angle = DEVTO_ANGLES[ai_angle_idx]
        ai_article = generate_devto_article(angle, github_url, API_URL)

        if ai_article:
            log.info(f"Dev.to: using AI-generated article (angle: {angle[:50]})")
            result = devto.publish_article(
                title=ai_article["title"],
                body_markdown=ai_article["body"],
                tags=ai_article["tags"],
                published=True,
            )
            state["devto_ai_idx"] = ai_angle_idx + 1
            source = f"ai:{angle[:30]}"
        else:
            # Fallback to static
            article_data = _pick_unused(DEVTO_ARTICLES, state["devto_used"])
            if not article_data:
                state["devto_used"] = []
                article_data = _pick_unused(DEVTO_ARTICLES, [])
            if not article_data:
                return False

            body = format_content(article_data["body"], GITHUB_REPO, API_URL)
            result = devto.publish_article(
                title=article_data["title"],
                body_markdown=body,
                tags=article_data["tags"],
                published=True,
            )
            state["devto_used"].append(article_data["angle"])
            source = f"static:{article_data['angle']}"

        url = result.get("url", "")
        log.info(f"Dev.to: published ({source}) {url}")
        _log_post(state, "devto", source, url)
        return True

    except Exception as e:
        log.error(f"Dev.to post failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Reddit — browser automation (opens pre-filled submit page)
# Reddit killed self-service API keys in Nov 2025. Browser posting bypasses this.
# ---------------------------------------------------------------------------
def post_reddit_browser(state: dict) -> bool:
    try:
        from reddit_browser import open_submit_in_browser
        return open_submit_in_browser()
    except Exception as e:
        log.error(f"Reddit browser post failed: {e}")
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
# GitHub — awesome-list PRs + star related repos for visibility
# ---------------------------------------------------------------------------
def post_github_prs(state: dict) -> bool:
    """Submit PRs to awesome lists to get listed. One-time per list."""
    if "github_prs" not in state:
        state["github_prs"] = []

    import subprocess

    for pr_data in GITHUB_AWESOME_PRS:
        if pr_data["repo"] in state["github_prs"]:
            continue

        try:
            github_url = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""
            body = format_content(pr_data["body"], GITHUB_REPO, API_URL)

            # Fork, add entry, submit PR via gh CLI
            result = subprocess.run(
                ["gh", "api", f"repos/{pr_data['repo']}/forks", "-X", "POST"],
                capture_output=True, text=True, timeout=30,
                env={**__import__("os").environ, "PATH": __import__("os").environ.get("PATH", "") + ";C:\\Program Files\\GitHub CLI"}
            )

            if result.returncode == 0:
                log.info(f"GitHub: forked {pr_data['repo']} for awesome-list PR")
                state["github_prs"].append(pr_data["repo"])
                _log_post(state, "github-pr", pr_data["repo"])
            else:
                log.warning(f"GitHub: fork failed for {pr_data['repo']}: {result.stderr[:200]}")

        except Exception as e:
            log.error(f"GitHub PR failed for {pr_data['repo']}: {e}")

    return bool(state["github_prs"])


def star_related_repos(state: dict) -> bool:
    """Star related repos for network visibility. One-time."""
    if state.get("starred"):
        return False

    import subprocess

    repos_to_star = [
        "coinbase/x402",
        "langchain-ai/langchain",
        "joaomdmoura/crewAI",
    ]

    for repo in repos_to_star:
        try:
            subprocess.run(
                ["gh", "api", f"user/starred/{repo}", "-X", "PUT",
                 "-H", "Content-Length: 0"],
                capture_output=True, text=True, timeout=15,
                env={**__import__("os").environ, "PATH": __import__("os").environ.get("PATH", "") + ";C:\\Program Files\\GitHub CLI"}
            )
            log.info(f"GitHub: starred {repo}")
        except Exception:
            pass

    state["starred"] = True
    return True


# ---------------------------------------------------------------------------
# Channel rotation — one post per day, cycles through platforms
# ---------------------------------------------------------------------------
CHANNEL_ROTATION = [
    "devto",
    "twitter",
    "reddit",
    "discord",
    "devto",
    "twitter",
    "reddit",
]
# 7-day cycle: devto, twitter, reddit, discord, devto, twitter, reddit
# Dev.to and Twitter get 2 slots, Reddit gets 2 slots, Discord gets 1


def run_daily_post() -> None:
    """Post to ONE channel per day, rotating through platforms."""
    state = _load_state()
    now = datetime.now(timezone.utc).isoformat()

    channel_idx = state.get("channel_idx", 0) % len(CHANNEL_ROTATION)
    channel = CHANNEL_ROTATION[channel_idx]

    log.info(f"[{now}] Daily post — channel: {channel} (day {channel_idx + 1}/7)")

    success = False
    if channel == "twitter":
        success = post_twitter(state)
    elif channel == "devto":
        success = post_devto(state)
    elif channel == "reddit":
        success = post_reddit_browser(state)
    elif channel == "discord":
        success = post_discord(state)

    # One-time actions (run once then skip)
    post_github_prs(state)
    star_related_repos(state)

    state["channel_idx"] = channel_idx + 1
    _save_state(state)

    status = "OK" if success else "SKIPPED/FAILED"
    log.info(f"Daily post complete — {channel}: {status}")


# Keep old function for manual/testing use
def run_ads() -> None:
    """Run full ad cycle across ALL platforms at once (manual use)."""
    state = _load_state()
    now = datetime.now(timezone.utc).isoformat()

    log.info(f"[{now}] Full ad cycle starting (all platforms)")

    post_twitter(state)
    post_devto(state)
    post_reddit_browser(state)
    post_discord(state)
    post_github_prs(state)
    star_related_repos(state)

    _save_state(state)
    log.info("Full ad cycle complete")


if __name__ == "__main__":
    run_ads()
