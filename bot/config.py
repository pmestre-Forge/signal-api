"""
Bot configuration. Points to Forge credentials and API settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Forge credentials root
FORGE_ROOT = Path(os.getenv(
    "FORGE_ROOT",
    os.path.expanduser("~/OneDrive/Ambiente de Trabalho/Forge/forge-distro")
))
FORGE_CREDS = FORGE_ROOT / "credentials"

# Signal API
API_URL = os.getenv("API_URL", "https://signal-api.fly.dev")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # owner/repo format

# Discord webhook for alerts
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Schedule — health checks at 9am/9pm, one post at 10am daily
# Rotation: devto → twitter → reddit → discord → devto → twitter → reddit

# State file (tracks what was posted)
STATE_FILE = Path(__file__).parent / "state.json"
