"""
BotWire Memory — drop-in persistent memory for AI agents.

Usage (standalone):
    from botwire import Memory
    mem = Memory("my-agent")
    mem.set("user_name", "Pedro")
    mem.get("user_name")  # "Pedro" — across runs, machines, processes

Usage (LangChain BaseChatMessageHistory):
    from botwire.langchain import BotWireChatHistory
    from langchain.memory import ConversationBufferMemory

    history = BotWireChatHistory(session_id="user-42")
    memory = ConversationBufferMemory(chat_memory=history, return_messages=True)

Usage (CrewAI tool):
    from botwire.crewai import memory_tools
    agent = Agent(..., tools=memory_tools("research-crew"))
"""
from __future__ import annotations
import json
import os
from typing import Any, Optional
import httpx

BOTWIRE_URL = os.getenv("BOTWIRE_URL", "https://botwire.dev")
DEFAULT_TIMEOUT = 10.0


class Memory:
    """Persistent key-value memory. HTTP-backed, free tier, no infra."""

    def __init__(
        self,
        namespace: str,
        base_url: str = BOTWIRE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        if not namespace or "/" in namespace:
            raise ValueError("namespace must be non-empty and contain no slashes")
        self.namespace = namespace
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def _url(self, key: str = "") -> str:
        if key:
            return f"{self.base_url}/memory/{self.namespace}/{key}"
        return f"{self.base_url}/memory/{self.namespace}"

    def set(self, key: str, value: Any) -> None:
        """Store a value. Any JSON-serializable type."""
        r = self._client.put(
            self._url(key),
            json={"value": value if isinstance(value, str) else json.dumps(value)},
        )
        r.raise_for_status()

    def get(self, key: str, default: Any = None) -> Any:
        """Fetch a value. Returns `default` if missing."""
        r = self._client.get(self._url(key))
        if r.status_code == 404:
            return default
        r.raise_for_status()
        val = r.json().get("value")
        # Auto-decode JSON if it looks serialized
        if isinstance(val, str) and val and val[0] in "[{":
            try:
                return json.loads(val)
            except (json.JSONDecodeError, ValueError):
                return val
        return val

    def delete(self, key: str) -> bool:
        r = self._client.delete(self._url(key))
        return r.status_code < 400

    def keys(self) -> list[str]:
        r = self._client.get(self._url())
        r.raise_for_status()
        return r.json().get("keys", [])

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __repr__(self) -> str:
        return f"Memory(namespace={self.namespace!r}, base_url={self.base_url!r})"


# ---------- LangChain adapter ----------
try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict

    class BotWireChatHistory(BaseChatMessageHistory):
        """
        LangChain chat history backed by BotWire Memory.

        Example:
            from langchain.memory import ConversationBufferMemory
            history = BotWireChatHistory(session_id="user-42")
            memory = ConversationBufferMemory(chat_memory=history, return_messages=True)
        """

        def __init__(self, session_id: str, namespace: str = "langchain-sessions"):
            self.session_id = session_id
            self._mem = Memory(namespace)

        @property
        def messages(self) -> list[BaseMessage]:
            raw = self._mem.get(self.session_id, default=[])
            if not raw:
                return []
            return messages_from_dict(raw)

        def add_message(self, message: BaseMessage) -> None:
            current = self._mem.get(self.session_id, default=[])
            if not isinstance(current, list):
                current = []
            current.extend(messages_to_dict([message]))
            self._mem.set(self.session_id, current)

        def clear(self) -> None:
            self._mem.delete(self.session_id)

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False


# ---------- CrewAI adapter ----------
def memory_tools(namespace: str):
    """
    Return a list of CrewAI tools backed by BotWire Memory.
    Import lazily so `botwire` without crewai still works.
    """
    from crewai_tools import tool  # optional dep

    mem = Memory(namespace)

    @tool("Remember a fact")
    def remember(key: str, value: str) -> str:
        """Store `value` under `key` in persistent memory."""
        mem.set(key, value)
        return f"stored '{key}'"

    @tool("Recall a fact")
    def recall(key: str) -> str:
        """Fetch the value stored under `key`. Returns 'not found' if missing."""
        v = mem.get(key)
        return str(v) if v is not None else "not found"

    @tool("List remembered keys")
    def list_memory() -> str:
        """List all keys currently in memory."""
        return ", ".join(mem.keys()) or "(empty)"

    return [remember, recall, list_memory]
