"""
API health monitor. Checks all 3 services and alerts Discord if anything is down.
"""

from datetime import datetime, timezone

import httpx

from config import API_URL, DISCORD_WEBHOOK_URL


def check_health() -> dict:
    """Check all 3 services: API core, Memory, Identity."""
    timestamp = datetime.now(timezone.utc).isoformat()
    results = {"timestamp": timestamp, "services": {}}
    any_down = False

    checks = {
        "api": f"{API_URL}/health",
        "memory": f"{API_URL}/stats/memory",
        "identity": f"{API_URL}/stats/identity",
    }

    for name, url in checks.items():
        try:
            r = httpx.get(url, timeout=10)
            ok = r.status_code == 200
            results["services"][name] = {
                "status": "up" if ok else "degraded",
                "code": r.status_code,
                "response_ms": int(r.elapsed.total_seconds() * 1000),
            }
            if not ok:
                any_down = True
        except Exception as e:
            results["services"][name] = {"status": "down", "error": str(e)}
            any_down = True

    results["status"] = "down" if any_down else "up"
    return results


def alert_discord(message: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
    except Exception:
        pass


def run_check() -> dict:
    result = check_health()
    services = result["services"]

    summary = " | ".join(f"{k}:{v['status']}" for k, v in services.items())
    print(f"[{result['timestamp']}] {summary}", flush=True)

    if result["status"] == "down":
        broken = [f"{k}: {v.get('error', f'HTTP {v.get('code', '?')}')}"
                  for k, v in services.items() if v["status"] != "up"]
        alert_discord(f"**SERVICE DOWN**\n" + "\n".join(broken))

    return result


if __name__ == "__main__":
    run_check()
