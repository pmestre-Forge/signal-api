"""
API health monitor. Pings the health endpoint and alerts Discord if down.
"""

from datetime import datetime, timezone

import httpx

from config import API_URL, DISCORD_WEBHOOK_URL


def check_health() -> dict:
    try:
        r = httpx.get(f"{API_URL}/health", timeout=10)
        return {
            "status": "up" if r.status_code == 200 else "degraded",
            "code": r.status_code,
            "response_ms": int(r.elapsed.total_seconds() * 1000),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "down",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def alert_discord(message: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception:
        pass


def run_check() -> dict:
    result = check_health()
    print(f"[{result['timestamp']}] API: {result['status']}", flush=True)

    if result["status"] == "down":
        alert_discord(f"**Signal API DOWN** | {result.get('error', 'unknown')}")
    elif result["status"] == "degraded":
        alert_discord(f"**Signal API DEGRADED** (HTTP {result['code']})")

    return result


if __name__ == "__main__":
    run_check()
