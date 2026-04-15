"""
Main bot runner.

    python run.py              # Run on schedule (monitor + ads)
    python run.py --monitor    # One-shot health check
    python run.py --advertise  # One-shot ad cycle
    python run.py --status     # Show what's been posted
"""

import json
import sys
import time

import schedule

from advertise import run_ads
from config import AD_INTERVAL_DAYS, MONITOR_INTERVAL_MINUTES, STATE_FILE
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
        print(f"  {p['timestamp'][:10]}  {p['platform']:10s}  {p['angle']:20s}  {url}")

    print(f"\nAngles remaining:")
    print(f"  Twitter: {4 - len(state.get('twitter_used', []))} of 4")
    print(f"  Reddit:  {4 - len(state.get('reddit_used', []))} of 4")
    print(f"  Dev.to:  {1 - len(state.get('devto_used', []))} of 1")
    print(f"  Discord: {2 - len(state.get('discord_used', []))} of 2")


def main():
    if "--monitor" in sys.argv:
        run_check()
        return

    if "--advertise" in sys.argv:
        run_ads()
        return

    if "--status" in sys.argv:
        cmd_status()
        return

    print("Signal API Bot", flush=True)
    print(f"  Monitor: every {MONITOR_INTERVAL_MINUTES} min", flush=True)
    print(f"  Advertise: every {AD_INTERVAL_DAYS} days", flush=True)
    print(f"  Platforms: Twitter/X, Dev.to, Reddit, Discord", flush=True)

    schedule.every(MONITOR_INTERVAL_MINUTES).minutes.do(run_check)
    schedule.every(AD_INTERVAL_DAYS).days.do(run_ads)

    # Run immediately on start
    run_check()
    run_ads()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
