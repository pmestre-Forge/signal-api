"""
BotWire Bot Runner — 2 posting schedules + health checks + channel bot.

    python run.py              # Run everything on schedule
    python run.py --monitor    # One-shot health check
    python run.py --post       # One-shot post cycle
    python run.py --status     # Show posting history
"""

import json
import sys
import time

import schedule

from advertise import run_daily_post
from config import STATE_FILE
from monitor import run_check

# Import product-specific posting
from generate import _today_product, PRODUCT_ROTATION


def post_product_spotlight():
    """Post about a specific product feature/use case. Runs 3x daily."""
    from advertise import post_discord, post_devto, _load_state, _save_state
    import random

    state = _load_state()
    product = _today_product()

    # Pick one platform per spotlight
    platforms = ["discord", "devto"]
    platform = random.choice(platforms)

    if platform == "discord":
        from content import DISCORD_POSTS, format_content
        from config import API_URL, GITHUB_REPO, DISCORD_WEBHOOK_URL
        import httpx

        if DISCORD_WEBHOOK_URL:
            msg = f"**{product['name']}** -- {product['focus']}\n\nTry it: {API_URL}\nDocs: {API_URL}/docs"
            try:
                httpx.post(DISCORD_WEBHOOK_URL, json={"content": msg}, timeout=10)
            except Exception:
                pass

    elif platform == "devto":
        post_devto(state)

    _save_state(state)


def cmd_status():
    """Show posting history."""
    if not STATE_FILE.exists():
        print("No posts yet.")
        return

    state = json.loads(STATE_FILE.read_text())
    posts = state.get("log", [])

    if not posts:
        print("No posts yet.")
        return

    print(f"\n{len(posts)} posts made:\n")
    for p in posts[-20:]:
        url = p.get("url", "")
        platform = p.get("platform", "?")
        angle = p.get("angle", "?")
        print(f"  {p['timestamp'][:10]}  {platform:18s}  {angle:25s}  {url}")


def main():
    if "--monitor" in sys.argv:
        run_check()
        return

    if "--post" in sys.argv:
        run_daily_post()
        return

    if "--status" in sys.argv:
        cmd_status()
        return

    print("BotWire Bot", flush=True)
    print("  Schedule:", flush=True)
    print("    Health:     9am + 9pm", flush=True)
    print("    Full post:  10am (all platforms, all products)", flush=True)
    print("    Spotlight:  12pm, 3pm, 6pm (one product, one platform)", flush=True)

    # Health checks
    schedule.every().day.at("09:00").do(run_check)
    schedule.every().day.at("21:00").do(run_check)

    # Full post — all platforms at 10am
    schedule.every().day.at("10:00").do(run_daily_post)

    # Product spotlights — 3x daily
    schedule.every().day.at("12:00").do(post_product_spotlight)
    schedule.every().day.at("15:00").do(post_product_spotlight)
    schedule.every().day.at("18:00").do(post_product_spotlight)

    # Health check on start
    run_check()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
