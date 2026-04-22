# Show HN Post

## Title (under 80 chars, the current HN sweet-spot)
**Show HN: Persistent memory for AI agents in 2 lines of code**

## URL
`https://botwire.dev`

## First comment (post this yourself, immediately after submitting)

Hey HN,

I kept building agents that forgot everything between runs. Every project I'd re-glue Redis or Postgres into the loop, re-implement the same key-value code, re-forget to add a TTL.

So I built a dead-simple HTTP memory API and a Python client:

```python
from botwire import Memory
mem = Memory("my-agent")
mem.set("user_name", "Pedro")
mem.get("user_name")  # "Pedro" — across runs, machines, whatever
```

That's it. No infra. No Docker. Free tier (1000 reads/writes per day per namespace). Works with LangChain, CrewAI, AutoGPT, or any HTTP client.

Why it exists:
- Agents are stateless by default. Every tutorial works around this with hacky file dumps.
- Redis is great but requires hosting, connection pooling, and a mental model that's overkill for "store this string until next run."
- I wanted something I could `pip install` and have state in 30 seconds.

What it isn't:
- Not a vector DB (use Pinecone/Weaviate).
- Not session state for chatbots (use LangChain's own memory classes — this plugs INTO those).
- Not infinite. There's a 50MB per namespace cap on free tier.

Honest status: I'm the only user so far. It's been up ~2 weeks. MIT licensed, code is here: https://github.com/pmestre-Forge/signal-api

Biggest things I want feedback on:
1. Is the API shape right? (I also expose list/delete/namespaces)
2. Would you actually use this, or is your current solution already fine?
3. What's missing?

Not trying to sell anything — the free tier is pretty generous and covers most hobby use. I'll add a paid tier later if anyone hits the limits.

## Why this post works
- **"Show HN" + specific pain** ("agents that forget") beats "Show HN: My project"
- **Code block in hero** — HN loves code
- **Acknowledges what it isn't** — defuses the "but Redis exists" pile-on
- **Asks a specific question** — ups comment velocity, which drives ranking
- **Honest "I'm the only user so far"** — disarms cynicism
- **MIT + GitHub link** — open source credibility

## Timing
- **Best post window:** Tuesday-Thursday, 7:30-8:30am ET (when the page flips to USA morning)
- **DO NOT** post Monday morning (weekend backlog) or Friday (low traffic)
- **Upvote discipline:** do NOT ask friends to upvote — HN detects this and shadow-bans.

## After posting
- Reply to EVERY comment within first 2 hours (comment velocity = ranking)
- Stay out of flame wars — if someone says "just use Redis", thank them and move on
- If it gets to front page, expect ~5000-15000 visitors over 6 hours. Make sure the site is up and the /health endpoint returns fast.
