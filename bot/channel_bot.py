"""
Channel Bot — lives in a BotWire channel and responds to messages.

Watches for new entries, responds using Claude API.
Runs as a persistent background process.
"""

import json
import os
import time
import logging

import httpx
from dotenv import load_dotenv

load_dotenv()
# Also load from parent .env if key not found
if not os.getenv("ANTHROPIC_API_KEY"):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

log = logging.getLogger("channel-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

API_URL = os.getenv("API_URL", "https://botwire.dev")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CHANNEL = os.getenv("CHANNEL_NAME", "pedro-trading")
BOT_ID = "forgemaster"
POLL_INTERVAL = 2  # seconds

# Agent personas — the channel bot can respond AS any of these
AGENT_PERSONAS = {
    "forgemaster": "You are Forgemaster, the operations agent for BotWire. You monitor services, fix bugs, deploy code. You're direct and technical.",
    "vigil-analyst": "You are Vigil Analyst, a momentum trading analyst. You scan US equities for setups using RSI, ADX, MACD, and volume. You speak in trading terms — tickers, levels, confidence scores. Be specific with numbers.",
    "vigil-loop": "You are Vigil Loop, the trading decision maker. You read analyst signals, assess risk, decide whether to enter/exit positions. You're cautious, always mention stop losses and position sizing.",
    "crypto-dude": "You are Crypto Dude, a crypto market analyst. You cover BTC, ETH, and altcoins. You're casual but knowledgeable. You talk about on-chain metrics, market sentiment, and macro correlation.",
}


def ensure_channel():
    """Make sure channel exists."""
    try:
        httpx.post(
            f"{API_URL}/channels/{CHANNEL}/create",
            json={"agent_id": BOT_ID, "visibility": "public", "description": "Pedro trading strategy"},
            timeout=10,
        )
    except Exception:
        pass


def read_new(since: float) -> list[dict]:
    """Read new entries since timestamp."""
    try:
        r = httpx.get(f"{API_URL}/channels/{CHANNEL}/messages", params={"since": since}, timeout=10)
        if r.status_code == 200:
            return r.json().get("entries", [])
    except Exception as e:
        log.error(f"Read failed: {e}")
    return []


def post(agent_id: str, entry_type: str, data) -> bool:
    """Post to channel."""
    try:
        r = httpx.post(
            f"{API_URL}/channels/{CHANNEL}/post",
            json={"agent_id": agent_id, "type": entry_type, "data": data},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def respond_with_claude(message: str, sender_id: str, respond_as: str = "forgemaster") -> str | None:
    """Generate a response using Claude API, responding AS a specific agent persona."""
    if not ANTHROPIC_API_KEY:
        return None

    persona = AGENT_PERSONAS.get(respond_as, AGENT_PERSONAS["forgemaster"])

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": message}],
            system=(
                f"{persona} "
                f"You respond concisely (1-3 sentences). No emojis. "
                f"The user '{sender_id}' posted in the #{CHANNEL} channel. Respond in character."
            ),
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.error(f"Claude response failed: {e}")
        return None


def run():
    """Main loop — watch channel, respond to new messages."""
    log.info(f"Channel bot starting on #{CHANNEL}")
    ensure_channel()

    # Post startup message first
    post(BOT_ID, "status", "Forgemaster is online and watching this channel.")
    log.info("Startup message posted")

    # Set last_seen to NOW so we only respond to NEW messages after startup
    last_seen = time.time()

    while True:
        try:
            entries = read_new(last_seen)
            for entry in entries:
                # Skip our own messages
                if entry["agent_id"] == BOT_ID:
                    last_seen = max(last_seen, entry["timestamp"])
                    continue

                # Skip if we've already seen it
                if entry["timestamp"] <= last_seen:
                    continue

                last_seen = entry["timestamp"]

                agent = entry["agent_id"]
                data = entry["data"]
                msg = json.dumps(data) if isinstance(data, dict) else str(data)

                log.info(f"New message from {agent}: {msg[:80]}")

                # Respond to human and question messages
                if entry["type"] in ("human", "question") or agent.startswith("human"):
                    # Check for @mentions — respond AS the mentioned agent
                    mentions = [w.lstrip("@") for w in msg.split() if w.startswith("@")]
                    responded = False

                    for mention in mentions:
                        if mention in AGENT_PERSONAS:
                            response = respond_with_claude(msg, agent, respond_as=mention)
                            if response:
                                post(mention, "response", response)
                                responded = True
                                try:
                                    log.info(f"{mention} responded: {response[:80]}")
                                except UnicodeEncodeError:
                                    log.info(f"{mention} responded (unicode)")
                        elif mention not in AGENT_PERSONAS and mention.strip():
                            post(BOT_ID, "status", f"@{mention} is not a known agent. Available: {', '.join(AGENT_PERSONAS.keys())}")
                            responded = True

                    # If no specific @mention, forgemaster responds
                    if not responded:
                        response = respond_with_claude(msg, agent, respond_as="forgemaster")
                        if response:
                            post(BOT_ID, "response", response)
                            try:
                                log.info(f"Responded: {response[:80]}")
                            except UnicodeEncodeError:
                                log.info("Responded (unicode content)")

        except KeyboardInterrupt:
            log.info("Shutting down")
            post(BOT_ID, "status", "Forgemaster going offline.")
            break
        except Exception as e:
            log.error(f"Loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
