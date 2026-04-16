"""
FORGEMASTER — Operations Module

Checks everything is alive. Fixes what's broken. Logs what happened.
"""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BOT_DIR = PROJECT_ROOT / "bot"
OPS_LOG = Path(__file__).parent / "ops_log.json"
API_URL = "https://botwire.dev"


def _log_ops(entry: dict) -> None:
    """Append to operations log."""
    entries = []
    if OPS_LOG.exists():
        try:
            entries = json.loads(OPS_LOG.read_text())
        except Exception:
            entries = []
    # Keep last 100 entries
    entries = entries[-99:]
    entries.append({**entry, "timestamp": datetime.now(timezone.utc).isoformat()})
    OPS_LOG.write_text(json.dumps(entries, indent=2))


def check_services() -> dict:
    """Check all 3 API services."""
    results = {}
    checks = {
        "api": f"{API_URL}/health",
        "memory": f"{API_URL}/stats/memory",
        "identity": f"{API_URL}/stats/identity",
        "context": f"{API_URL}/pricing",
    }
    for name, url in checks.items():
        try:
            r = httpx.get(url, timeout=15)
            results[name] = {
                "status": "up" if r.status_code == 200 else "degraded",
                "code": r.status_code,
                "ms": int(r.elapsed.total_seconds() * 1000),
            }
        except Exception as e:
            results[name] = {"status": "down", "error": str(e)[:200]}

    return results


def check_bot_alive() -> dict:
    """Check if the advertising bot process is running."""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        bot_running = "run.py" in result.stdout and "signal-api" in result.stdout
        return {"alive": bot_running}
    except Exception:
        # Windows fallback
        try:
            result = subprocess.run(
                ["tasklist"], capture_output=True, text=True, timeout=5
            )
            bot_running = "python" in result.stdout.lower()
            return {"alive": bot_running, "note": "windows-tasklist-check"}
        except Exception as e:
            return {"alive": False, "error": str(e)[:200]}


def restart_bot() -> dict:
    """Restart the advertising bot."""
    try:
        # Kill existing
        subprocess.run(["pkill", "-f", "bot/run.py"], capture_output=True, timeout=5)
        time.sleep(1)

        # Start new
        subprocess.Popen(
            ["python", "bot/run.py"],
            cwd=str(PROJECT_ROOT),
            stdout=open(str(BOT_DIR / "bot.log"), "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        time.sleep(2)

        # Verify
        bot_check = check_bot_alive()
        _log_ops({"action": "restart_bot", "result": bot_check})
        return {"restarted": True, **bot_check}
    except Exception as e:
        _log_ops({"action": "restart_bot", "error": str(e)})
        return {"restarted": False, "error": str(e)[:200]}


def check_bot_posts_today() -> dict:
    """Check if today's posts went out."""
    state_file = BOT_DIR / "state.json"
    if not state_file.exists():
        return {"posts_today": 0, "state_exists": False}

    try:
        state = json.loads(state_file.read_text())
        logs = state.get("log", [])
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_posts = [p for p in logs if p.get("timestamp", "").startswith(today)]
        return {
            "posts_today": len(today_posts),
            "platforms": list(set(p.get("platform", "?") for p in today_posts)),
            "total_posts": len(logs),
        }
    except Exception as e:
        return {"posts_today": 0, "error": str(e)[:200]}


def check_github_pat() -> dict:
    """Check if GitHub PAT is close to expiring."""
    creds_path = Path.home() / "OneDrive" / "Ambiente de Trabalho" / "Forge" / "forge-distro" / "credentials" / "github.json"
    if not creds_path.exists():
        return {"status": "no_credentials_file"}

    try:
        creds = json.loads(creds_path.read_text())
        expires = creds.get("expires", "")
        if not expires:
            return {"status": "no_expiry_set"}

        from datetime import datetime as dt
        exp_date = dt.strptime(expires, "%Y-%m-%d")
        days_left = (exp_date - dt.now()).days
        return {
            "expires": expires,
            "days_left": days_left,
            "urgent": days_left <= 3,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def run_operations() -> dict:
    """Full operations check. Returns report dict."""
    report = {
        "services": check_services(),
        "bot": check_bot_alive(),
        "posts": check_bot_posts_today(),
        "github_pat": check_github_pat(),
        "actions_taken": [],
    }

    # Auto-fix: restart bot if dead
    if not report["bot"].get("alive", False):
        restart = restart_bot()
        report["actions_taken"].append(f"Bot was dead. Restarted: {restart.get('restarted')}")

    # Log services status
    all_up = all(v.get("status") == "up" for v in report["services"].values())
    if not all_up:
        down = [k for k, v in report["services"].items() if v.get("status") != "up"]
        report["actions_taken"].append(f"Services degraded/down: {down}")
        _log_ops({"action": "services_check", "down": down})

    # GitHub PAT warning
    pat = report["github_pat"]
    if pat.get("urgent"):
        report["actions_taken"].append(f"GitHub PAT expires in {pat['days_left']} days! Pedro must renew.")

    _log_ops({"action": "full_check", "all_up": all_up, "bot_alive": report["bot"].get("alive"),
              "posts_today": report["posts"].get("posts_today", 0)})

    return report


if __name__ == "__main__":
    import pprint
    pprint.pprint(run_operations())
