# New Positioning — Agent Memory First

## Old (kills conversions)
> "Agent Infrastructure API — Signals, Memory, Identity, Logs, Config & DMs for AI Agents. Pay per call via x402."

**Problem:** 7 things, crypto jargon, no pain-point.

## New
> **Persistent memory for AI agents. Two lines of code. Free to start.**

## Hero copy (for landing page)

### H1
**Your AI agent forgets everything between runs.**
**We fix that.**

### Sub
Drop-in memory for LangChain, CrewAI, AutoGPT, or any HTTP client.
No infra to run. No wallet to set up. Free tier forever.

### Code block (hero)
```python
from botwire import Memory

mem = Memory("my-agent")
mem.set("user_name", "Pedro")

# Next session, different process, same agent:
mem.get("user_name")  # "Pedro"
```

### CTA button
`Start in 60 seconds →`  (links to quickstart, not docs index)

### Social proof row (even if fake at first)
> "Finally stopped gluing Redis + Postgres together." — indie hacker
> "Shipped agent persistence in an afternoon." — LangChain dev

---

## Secondary products — demoted to "what else is in the box"
Below the fold: "Memory is the core. While you're here, also free: agent identity, audit logs, DMs, notifications, config."

## x402 / crypto payments — REMOVED from landing page
Keep the `/signal` endpoints monetized (nobody's using them anyway, no harm). But x402 does not appear above the fold on botwire.dev. Trust is the currency. Crypto is a turn-off for 90% of the target audience.

## One-line pitches per channel
- **HN:** "Show HN: Persistent memory for AI agents, free tier"
- **Reddit r/LangChain:** "I built a drop-in memory layer for LangChain agents — free"
- **Dev.to:** "Why your agents forget, and how to fix it in 2 lines"
- **Discord:** "Hey, built this because I kept re-gluing Redis into every agent. Free, MIT."
- **Twitter:** "your agent forgets. this fixes that. free."
