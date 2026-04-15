"""
Main bot runner.

    python run.py              # Run on schedule (1 post/day, 2 health checks/day)
    python run.py --monitor    # One-shot health check
    python run.py --post       # One-shot daily post (one channel)
    python run.py --advertise  # One-shot full blast (all channels)
    python run.py --status     # Show what's been posted
"""

import json
import sys
import time

import schedule

from advertise import run_daily_post, run_ads
from config import STATE_FILE
from monitor import run_check


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

    from advertise import CHANNEL_ROTATION
    channel_idx = state.get("channel_idx", 0) % len(CHANNEL_ROTATION)
    next_channel = CHANNEL_ROTATION[channel_idx]

    print(f"\nNext post: {next_channel} (day {channel_idx + 1}/7)")
    print(f"\n7-day rotation: devto -> twitter -> reddit -> discord -> devto -> twitter -> reddit")


def main():
    if "--monitor" in sys.argv:
        run_check()
        return

    if "--post" in sys.argv:
        run_daily_post()
        return

    if "--advertise" in sys.argv:
        run_ads()
        return

    if "--status" in sys.argv:
        cmd_status()
        return

    print("Signal API Bot", flush=True)
    print("  Schedule:", flush=True)
    print("    Health check: 9am + 9pm", flush=True)
    print("    Daily post:   10am (one channel per day)", flush=True)
    print("    Rotation:     devto -> twitter -> reddit -> discord -> devto -> twitter -> reddit", flush=True)

    # Health checks at 9am and 9pm
    schedule.every().day.at("09:00").do(run_check)
    schedule.every().day.at("21:00").do(run_check)

    # One post per day at 10am
    schedule.every().day.at("10:00").do(run_daily_post)

    # Run health check immediately on start
    run_check()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
