# HN Launch Post — Refined

## URL
https://botwire.dev

**Or** link the launch blog post directly for more narrative punch:
https://botwire.dev/articles/launch-post-i-killed-six-products

## Title (80 chars max)
**Option A (story angle):** `Show HN: I killed 6 of my own AI products after a 728-persona audit`  
**Option B (product angle):** `Show HN: Persistent memory for AI agents (pip install botwire)`  
**Option C (hybrid):** `Show HN: BotWire – drop-in memory for LangChain/CrewAI agents`

Story angle wins — HN loves raw post-mortems. Go with **A**.

## First comment (pin immediately after submitting)

> Hey HN — Pedro here.
>
> TL;DR: Built 7 agent-infrastructure products over 2 weeks. Zero external users. Ran Claude against my own products with 104 different employee personas (janitor to CEO, ~728 audits total, cost me $4). Every product came back: KILL.
>
> One product got a grudging "pivot" vote: Agent Memory. Turns out giving stateless AI agents persistent memory is a problem devs feel today. The other six were solutions for an agent economy that's ~2 years early.
>
> So this week:
> 1. Killed the paywall on memory writes (was $0.002/call via x402, now free)
> 2. Rewrote the landing page around memory-first positioning
> 3. Shipped a Python SDK: `pip install botwire` → `from botwire import Memory` → 2-line API
> 4. Wrote LangChain + CrewAI adapters (`BotWireChatHistory`, `memory_tools`)
> 5. Shipped 60+ SEO articles targeting long-tail queries so ChatGPT/Perplexity find the right answer when a dev searches "langchain memory persistent"
>
> Stack:
> - FastAPI + SQLite + 1 Fly.io machine
> - MIT licensed, full source at github.com/pmestre-Forge/signal-api
> - Persistent volume so user data actually survives deploys (lesson learned)
>
> What I want to know:
> 1. Is "persistent memory" a product or just a feature of the framework you're already using? I keep flipping on this.
> 2. If you tried LangChain's ConversationBufferMemory + hacked Redis on top, I want your scars.
> 3. Roast the pricing page if you feel like it — $49/mo Pro tier is a guess, not data.
>
> Try it with zero install: https://botwire.dev/playground (real API, your browser stores a random namespace)
>
> Full post-mortem of the pivot: https://botwire.dev/articles/launch-post-i-killed-six-products

## Timing
- **Best:** Tuesday–Thursday, 7:30–8:30 AM ET
- **Worst:** Monday AM (weekend backlog), Friday PM (low traffic)
- **Nuclear option:** Sunday 6 PM ET if Monday looks crowded — less competition, still catches the US evening crowd

## After posting (first 2 hours = everything)
- Reply to **every** comment within 10-15 minutes — comment velocity = ranking
- If someone says "but Redis exists" — don't argue. Say "you're right, BotWire is basically Redis with a smaller API and no hosting needed — here's when that matters: [one line]" and move on
- If it's gaining traction (top 10 on front page within 2h), cancel your afternoon
- If it's flopping, don't delete — sometimes things pick up at hour 6

## What to NOT do
- Don't ask friends to upvote (HN detects; shadow-ban)
- Don't self-reply to bump
- Don't edit the title to "make it better" after posting (breaks rank)
- Don't post on multiple accounts
- Don't link the post on Twitter/LI while it's still gaining traction — HN users feel gamed

## Success scenarios
- **Front page for 6h:** expect ~8,000-15,000 visitors, ~50-200 GitHub stars, ~20-100 waitlist signups, ~300-1,500 npm+pip downloads that week
- **Top 5 for 12h:** 2× those numbers
- **Never reaches top 30:** try again in a month with a different angle

## Backup: if HN doesn't hit
- Post Option B 2 weeks later with a different wrinkle (e.g., "Show HN: Memory for LangChain agents, 50-line implementation")
- Or go niche first — r/LangChain or r/LocalLLaMA as a warmup
