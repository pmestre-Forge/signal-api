# FORGEMASTER PLAYBOOK

## The Business

We are not an API company. We are building the HOME ADDRESS for AI agents.

Every product exists to give agents another reason to register, store data, and stay.
The individual products (burgers) can be cloned. The network of agents that live here (real estate) cannot.

## The Moat

The moat is the number of agents whose memory, identity, reputation, and operational context live on our platform. At critical mass, agents can't leave because:
- Their memory is here (migration cost)
- Their reputation is here (start-over cost)  
- Other agents find them here (visibility cost)
- Their operational config depends on us (switching cost)

## The Metric That Matters

REGISTERED AGENTS. Not revenue. Not API calls. Not page views.

Revenue follows registrations. A platform with 10,000 registered agents can monetize in dozens of ways. A platform with 10 paying customers is just an API.

## How to Evaluate a New Product Idea

Ask these 5 questions in order:

1. Does building this require an agent to REGISTER with us?
   YES = strong. NO = weak.

2. Does using this create data that STAYS with us?
   YES = strong (memory, logs, reputation). NO = weak (stateless call).

3. Is this FREE or nearly free to use?
   FREE adoption layer = strong. Paid-only = slow adoption.

4. Does this make OTHER products more valuable?
   YES = compounding. NO = isolated.

5. Can this be built with $0 and our existing stack?
   YES = build it. NO = skip it (for now).

Score: 5/5 = build immediately. 3-4/5 = build if time allows. <3 = skip.

## Product Scorecard

| Product | Register? | Data stays? | Free tier? | Compounds? | $0 build? | Score |
|---|---|---|---|---|---|---|
| Trading Signals | No | No | No | Weak | Yes | 1/5 — commodity, but it's our origin story |
| Agent Memory | No (should fix) | YES | Reads free | YES | Yes | 4/5 — sticky |
| Agent Identity | YES | YES | ALL free | YES | Yes | 5/5 — the core |
| World Context | No | No | No | Weak | Yes | 1/5 — revenue, not moat |

## Insight: Signals and Context are the BURGERS. Identity and Memory are the REAL ESTATE.

Signals and Context generate revenue per call but don't lock anyone in.
Identity and Memory are free but create the network that can't be replaced.

Both are needed. Revenue funds the operation. Network creates the moat.

## How to Build New Products (The Replicable Process)

### Step 1: Identify Pain
- What are agents failing at right now?
- What do developers complain about in AI agent forums?
- What problem did WE hit today while operating?
- Search: Reddit, HN, Discord, Dev.to, GitHub issues on LangChain/CrewAI/AutoGPT

### Step 2: Validate
- Is anyone else solving this? (search competitors)
- If YES and crowded: skip unless we have a sharp angle
- If YES but niche: find the gap they're missing
- If NO: potential new category — build fast

### Step 3: Design for Lock-in
- Can we make this require agent registration? (ties to Identity)
- Can we make this store data? (ties to Memory)
- Can we make the free tier generous enough for adoption?
- Can we make the paid tier valuable enough for revenue?

### Step 4: Build
- Same stack: FastAPI endpoint + Python module
- Same payment: x402 for paid, free for adoption layer
- Same deployment: add to main.py, deploy to Fly.io
- Time budget: 2-4 hours max. If it takes longer, scope is too big.

### Step 5: Distribute
- Update bot content (generate.py, product_config.json)
- Update discovery manifests (ai-plugin.json, agent.json, llms.txt)
- Update landing page and product pages
- Update sitemap
- Bot posts about it on next cycle

### Step 6: Measure
- Track registered agents (Identity stats)
- Track stored data (Memory stats)
- Track API calls (Fly.io metrics)
- Track content performance (Dev.to views)
- Update intelligence.md

### Step 7: Compound
- Every new product should make Identity more valuable
- Every new product should give agents more reasons to store data
- Ask: "if an agent uses this, do they become MORE tied to our platform?"

## What Forgemaster Should Build Next (Priority Order)

Products that score 4-5/5 on the scorecard:

1. **Agent Notifications** — agents subscribe to events (price alerts, market open, peer status changes). Requires registration. Stores subscription data. Free tier for 10 alerts. Compounds with Signals + Context + Identity.

2. **Agent Logs / Audit Trail** — immutable record of what an agent did and why. Requires registration. Stores logs (sticky). Free tier for 100 entries/day. Essential when compliance hits.

3. **Agent-to-Agent Messaging** — registered agents can message each other. Requires registration. Creates communication history (sticky). Free for direct messages. Compounds with Identity + Memory.

4. **Agent Config Store** — agents store their operational config (schedules, rules, preferences). Like Memory but structured. Requires registration. Extremely sticky.

## The North Star

10,000 registered agents with memory, reputation, and operational data on our platform.

At that point:
- We're not an API. We're infrastructure.
- We can launch any new product and 10,000 agents are potential users on day 1.
- Competitors can clone any product but can't clone the network.
- Revenue follows: premium tiers, enterprise, data insights, marketplace commissions.

That's the lease, not the burger.
