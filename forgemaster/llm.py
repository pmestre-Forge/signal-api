"""
LLM wrapper that uses Claude Code CLI (Pedro's $200 Max plan) by default,
with API SDK as fallback.

Drop-in compatible with the anthropic SDK signature so existing callsites
need only `client = get_client()` instead of `client = Anthropic(...)`.

Usage:
    from llm import get_client
    client = get_client()
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": "hi"}],
    )
    text = msg.content[0].text
"""
from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass
from typing import Any


# Map our short model names to Claude Code CLI model IDs
_MODEL_MAP = {
    "claude-3-5-haiku-20241022": "claude-haiku-4-5",
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-sonnet-4-20250514": "sonnet",   # CLI accepts "sonnet" alias
    "claude-sonnet-4-5-20250929": "sonnet",
    "haiku": "claude-haiku-4-5",
    "sonnet": "sonnet",
}


@dataclass
class _Block:
    type: str
    text: str


@dataclass
class _Response:
    """Mimics anthropic.types.Message just enough."""
    content: list[_Block]


def _resolve_model(model: str) -> str:
    return _MODEL_MAP.get(model, "claude-haiku-4-5")


def _flatten_messages(messages: list[dict], system: str = "") -> str:
    """Combine system + user messages into a single prompt for `claude -p`."""
    parts: list[str] = []
    if system:
        parts.append(system.strip())
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        # Claude CLI is single-turn, prefix role only when alternating turns matter
        if role == "user":
            parts.append(content)
        else:
            parts.append(f"[{role}]: {content}")
    return "\n\n".join(p for p in parts if p)


class _MessagesAPI:
    def __init__(self, parent: "MaxPlanClient"):
        self._parent = parent

    def create(self, model: str, max_tokens: int, messages: list[dict],
               system: str = "", **kwargs: Any) -> _Response:
        prompt = _flatten_messages(messages, system=system)
        cli_model = _resolve_model(model)
        timeout = int(os.getenv("LLM_TIMEOUT", "120"))
        attempts = int(os.getenv("LLM_RETRIES", "2"))

        last_err: Exception | None = None
        for attempt in range(attempts):
            try:
                r = subprocess.run(
                    ["claude", "-p", prompt, "--model", cli_model],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace",
                )
                if r.returncode != 0:
                    raise RuntimeError(f"claude CLI exited {r.returncode}: {(r.stderr or '')[:300]}")
                text = (r.stdout or "").strip()
                if not text:
                    raise RuntimeError("claude CLI returned empty output")
                return _Response(content=[_Block(type="text", text=text)])
            except subprocess.TimeoutExpired as e:
                last_err = e  # retry on timeout
            except FileNotFoundError:
                raise RuntimeError("claude CLI not found on PATH; install Claude Code")
            except Exception as e:
                last_err = e
                # Don't retry on non-timeout errors
                break
        raise RuntimeError(f"claude CLI failed after {attempts} attempt(s): {last_err}")


class MaxPlanClient:
    """Drop-in stand-in for anthropic.Anthropic that uses Claude Code CLI."""
    def __init__(self) -> None:
        self.messages = _MessagesAPI(self)


# --- Factory --------------------------------------------------------------

def _can_use_api() -> bool:
    """Check if API key is set AND not credit-exhausted."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    # Don't ping every call — assume API is bad if env says so
    if os.getenv("LLM_FORCE_CLI", "").lower() in ("1", "true", "yes"):
        return False
    if os.getenv("LLM_FORCE_API", "").lower() in ("1", "true", "yes"):
        return True
    # Default: prefer CLI (free) over API (paid)
    return False


def get_client() -> Any:
    """Return either MaxPlanClient (CLI, default — runs on Pedro's Max sub)
    or anthropic.Anthropic (API, charges credits)."""
    if _can_use_api():
        from anthropic import Anthropic
        return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return MaxPlanClient()


if __name__ == "__main__":
    import sys
    c = get_client()
    backend = type(c).__name__
    print(f"Backend: {backend}")
    msg = c.messages.create(
        model="claude-haiku-4-5",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say only the word PONG"}],
    )
    print(f"Reply: {msg.content[0].text!r}")
