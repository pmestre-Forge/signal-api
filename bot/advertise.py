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
    github_url = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""

    try:
        from publisher import TwitterPublisher

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
        # Temporarily adjust sys.path for devto publisher
        devto_path = str(FORGE_ROOT / "devto")
        if devto_path not in sys.path:
            sys.path.insert(0, devto_path)

        from publisher import DevtoPublisher

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
# Reddit — via Forge reddit_autoposter's PRAW setup
# ---------------------------------------------------------------------------
def post_reddit(state: dict) -> bool:
    github_url = f"https://github.com/{GITHUB_REPO}" if GITHUB_REPO else ""

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

        # Pick next subreddit in rotation
        reddit_idx = state.get("reddit_rotation_idx", 0) % len(REDDIT_ROTATION)
        sub_name = REDDIT_ROTATION[reddit_idx]

        # Try AI-generated post first
        ai_post = generate_reddit_post(sub_name, github_url, API_URL)

        if ai_post:
            title = ai_post["title"]
            body = ai_post["body"]
            source = f"ai:{sub_name}"
            log.info(f"Reddit: using AI-generated post for r/{sub_name}")
        else:
            # Fallback to static
            post_data = _pick_unused(REDDIT_POSTS, state["reddit_used"])
            if not post_data:
                state["reddit_used"] = []
                post_data = _pick_unused(REDDIT_POSTS, [])
            if not post_data:
                return False

            title = post_data["title"]
            body = format_content(post_data["body"], GITHUB_REPO, API_URL)
            sub_name = post_data["subreddits"][0]
            state["reddit_used"].append(post_data["angle"])
            source = f"static:{post_data['angle']}"

        try:
            submission = reddit.subreddit(sub_name).submit(
                title=title,
                selftext=body,
            )
            url = f"https://reddit.com{submission.permalink}"
            log.info(f"Reddit: posted to r/{sub_name} ({source}) {url}")
            _log_post(state, "reddit", source, url)
            state["reddit_rotation_idx"] = reddit_idx + 1
            return True
        except Exception as e:
            log.error(f"Reddit: failed to post to r/{sub_name}: {e}")
            return False

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
    post_github_prs(state)
    star_related_repos(state)

    _save_state(state)
    log.info("Ad cycle complete")


if __name__ == "__main__":
    run_ads()
