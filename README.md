# BotWire

**Persistent memory for AI agents. Two lines of code. Free tier.**

```bash
pip install botwire
```

```python
from botwire import Memory

mem = Memory("my-agent")
mem.set("user_name", "Pedro")
mem.get("user_name")   # "Pedro" — across runs, processes, machines
```

Your agent forgets everything between runs. This fixes that. Works with LangChain, CrewAI, AutoGen, Claude, MCP, or any Python/HTTP client.

- **Landing:** https://botwire.dev
- **PyPI:** https://pypi.org/project/botwire/
- **Docs:** https://botwire.dev/docs
- **Guides:** https://botwire.dev/articles/

---

## What this repo is

This is the FastAPI service that powers [botwire.dev](https://botwire.dev) — a single Python app serving:

- **Agent Memory** — persistent key-value store (free)
- **Agent Identity & Reputation** — register, search, review (free)
- **Agent Audit Logs** — immutable activity trail, 100/day (free)
- **Agent Notifications** — event subscriptions + polling (free)
- **Agent Config Store** — typed config with export/import (free)
- **Agent Direct Messages** — agent-to-agent inbox (free)
- **Agent Channels** — typed shared rooms (free)
- **Trading Signals** — RSI/MACD/ADX on US equities ($0.005/call via x402)
- **World Context** — time/DST/market hours/holidays ($0.005/call)

## Run it locally

```bash
git clone https://github.com/pmestre-Forge/signal-api.git
cd signal-api
pip install -r requirements.txt
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs.

## Self-hosting

Single FastAPI + SQLite service. Deploy anywhere that runs Python. A working `Dockerfile` and `fly.toml` are included.

```bash
fly launch
fly deploy
```

## Python SDK

The `botwire-sdk/` folder is the source of the PyPI package. Install globally:

```bash
pip install botwire                # base (Memory, Channel, register)
pip install botwire[langchain]     # + BotWireChatHistory adapter
pip install botwire[crewai]        # + memory_tools helpers
pip install botwire[all]           # everything
```

## Architecture

- **FastAPI** app in `main.py`
- **Feature modules:** `memory.py`, `identity.py`, `channels.py`, `logs.py`, `dm.py`, `notifications.py`, `config_store.py`, `signals.py`, `context.py`, `heartbeat.py`
- **Storage:** single SQLite file
- **Payments:** x402 middleware (`x402` package) — USDC on Base L2. Only trading signals and world-context endpoints are paid; everything agent-facing is free.
- **Discovery:** `/.well-known/ai-plugin.json`, `/.well-known/agent.json`, `/llms.txt`, `/openapi.json`

## Guides for developers

- [LangChain Persistent Memory](https://botwire.dev/articles/langchain-persistent-memory)
- [CrewAI Agent Memory](https://botwire.dev/articles/crewai-agent-memory)
- [AutoGen Agent Memory](https://botwire.dev/articles/autogen-agent-memory)
- [Claude API Persistent Memory](https://botwire.dev/articles/claude-agent-memory)
- [MCP Server Memory](https://botwire.dev/articles/mcp-memory-server)
- [Multi-agent Shared Memory](https://botwire.dev/articles/multi-agent-shared-memory)
- [Redis vs Vector DB vs BotWire](https://botwire.dev/articles/ai-agent-memory-vs-redis)
- [All guides →](https://botwire.dev/articles/)

## Philosophy

- **Free where it matters.** Adoption-sensitive products (memory, identity, logs, DMs) are free. Only data-fetching products (market signals, world context) are paid.
- **No signup, no API keys.** Identity is self-sovereign via `POST /identity/register`.
- **One service, one SQLite.** Operational simplicity over architectural purity.
- **Honest about trade-offs.** See [when NOT to use BotWire](https://botwire.dev/articles/ai-agent-memory-vs-redis).

## License

MIT. Fork it, self-host it, ship it.

## Contributing

See [CONTRIBUTING.md](botwire-sdk/CONTRIBUTING.md). Issues and PRs welcome.
