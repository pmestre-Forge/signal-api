# Product Hunt Launch Kit — BotWire Memory

## Launch window
- **Best day:** Tuesday or Wednesday
- **Best time:** 12:01 AM Pacific (you're getting a full 24h of attention)
- **Avoid:** Monday (crowded by reset), Saturday (low traffic)

## Submission fields

### Name
`BotWire`

### Tagline (60 chars max)
**Option A:** `Persistent memory for AI agents in 2 lines of code`  
**Option B:** `Your AI agent forgets. Two lines fix that.`  
**Option C:** `The memory primitive that was missing from LangChain`

Go with **A** — it's the most searchable and the least gimmicky.

### Description (260 chars max)
> Your AI agent forgets everything between runs. BotWire gives it persistent memory — `pip install botwire; from botwire import Memory`. Drop-in for LangChain, CrewAI, AutoGen, Claude, MCP. Free forever. MIT licensed. No signup.

### Topics (pick 4)
- Developer Tools
- Artificial Intelligence
- Open Source
- SaaS

### Media to upload
1. **Hero image (1270×760):** Screenshot of the landing page (https://botwire.dev)
2. **Gallery #1:** Screenshot of the playground (https://botwire.dev/playground)
3. **Gallery #2:** Code snippet screenshot — the 2-line example
4. **Gallery #3:** Status page showing real stats (https://botwire.dev/status)
5. **GIF (recommended):** The 90-second demo from `forgemaster/plays/05_demo_script.md` — agent forgets → agent remembers. Record with `vhs` from Charmbracelet.

### Pricing mention
> **Free:** Unlimited reads, 1,000 writes/day/namespace, 50MB/namespace  
> **Pro ($49/mo):** Coming soon — join the waitlist at /pricing

### Maker comment (pin this as first comment)

> Hey PH — I'm Pedro, solo founder.
>
> Background: I spent 2 weeks building 7 different AI agent services (trading signals, memory, identity, logs, DMs, etc). Got zero external users. Ran a 728-persona audit on my own products (full writeup on the landing page). Verdict: Memory is the only thing devs actually need today. Everything else was infrastructure for an agent economy that's 2 years early.
>
> So I killed six products this week, freed up the Memory API (was $0.002/write, now free), rewrote everything around that one thing, and shipped it here.
>
> What's in the box:
> - `pip install botwire` — memory in 2 lines
> - Works with LangChain (`BotWireChatHistory`), CrewAI (`memory_tools`), AutoGen, Claude, MCP
> - Free tier forever — 1k writes/day/namespace
> - MIT licensed — self-host if you want
> - 60+ framework-specific guides at botwire.dev/articles/
> - Live playground at botwire.dev/playground
>
> Asking for:
> 1. Upvote if the problem resonates
> 2. Try the playground (no signup, 30s)
> 3. Tell me if "persistent memory" is a product or a feature — I have theories but you have better ones
>
> Thanks 🙏

## Hunter (if you don't hunt yourself)
Good options who often hunt dev tools:
- Chris Messina (@chrismessina) — prolific hunter
- Kevin William David — frequent dev-tool hunts
- Fabrizio Rinaldi (@linuz90) — open-source friendly

**Ask:** DM them 24h before launch with a one-paragraph pitch and the URL. Let them look at it. Don't beg.

## Post-launch actions (first 24h)
- Reply to every single comment within 1h (PH ranks by engagement velocity)
- Share the launch URL on Twitter, LinkedIn, your personal Slack, any dev communities where it's appropriate
- **Do not** mass-DM friends asking them to upvote — PH detects this and penalizes
- Update the pinned comment every few hours with a "status" (e.g., "100 installs in 6h, thanks!")
- Screenshot any nice tweet/comment about it and RT/quote

## Follow-up (day 2-7)
- Email everyone who joined the Pro waitlist during PH (you'll have a list in /stats/memory — check the `waitlist` namespace)
- Post a "what PH taught me" thread on Twitter with raw numbers — high engagement

## Metrics to track
- Upvotes at 24h (anything >100 = good day; >300 = trending)
- Visits to botwire.dev
- Installs (via pypistats.org for botwire)
- Waitlist signups
- GitHub stars
