# Partnership Outreach Drafts — 10 Emails

**Send from:** `p.mestre@live.com.pt`
**Goal per email:** Get BotWire listed in their docs, community package, or ecosystem page. Backlinks + implicit endorsement.

---

## 1. LangChain partnerships

**To:** partnerships@langchain.com (or contact@)
**Subject:** `BotWire memory adapter for langchain-community`

> Hi LangChain team,
>
> I built a drop-in `BaseChatMessageHistory` adapter called `BotWireChatHistory` that gives LangChain agents HTTP-backed persistent memory with zero infrastructure setup. It's available now via `pip install botwire[langchain]`.
>
> I'd love to contribute it upstream to `langchain-community` so users can `from langchain_community.chat_message_histories import BotWireChatHistory`. Is there an intake process I should follow, or should I just open a PR?
>
> Docs: https://botwire.dev/articles/langchain-persistent-memory
> SDK: https://pypi.org/project/botwire/
> Source: MIT, github.com/pmestre-Forge/signal-api
>
> — Pedro

---

## 2. CrewAI partnerships

**To:** hello@crewai.com
**Subject:** `CrewAI persistent memory tools — open-source drop-in`

> Hi CrewAI team,
>
> I shipped three tools (`remember`, `recall`, `list_memory`) that make any CrewAI agent stateful across kickoff() calls, backed by a free HTTP API. Available as `from botwire.memory import memory_tools` via `pip install botwire[crewai]`.
>
> Would love to be listed in your "tools" ecosystem or docs. Happy to open a PR against crewAI-tools if that's the right path.
>
> Guide: https://botwire.dev/articles/crewai-agent-memory
> Quickstart: https://botwire.dev/articles/quickstart-crewai
>
> — Pedro

---

## 3. Anthropic — MCP directory

**To:** mcp@anthropic.com (or via the MCP discord)
**Subject:** `botwire-mcp server submission`

> Hi Anthropic team,
>
> I built an MCP server (`botwire-mcp`) that exposes persistent key-value memory as four tools: remember, recall, forget, list_memory. Designed for Claude Desktop. Zero signup, free tier.
>
> Happy to be listed in the MCP servers directory if there's one — or to submit to your community registry if that's the path. Config example in the README.
>
> Source: github.com/pmestre-Forge/signal-api/tree/main/botwire-mcp
> Guide: https://botwire.dev/articles/mcp-memory-server
>
> — Pedro

---

## 4. Vercel AI SDK team

**To:** ai-sdk@vercel.com (or via vercel.com/help)
**Subject:** `BotWire memory for Vercel AI SDK — guide submission`

> Hi Vercel team,
>
> I wrote a guide on adding persistent memory to Vercel AI SDK apps using a free HTTP API that runs on edge (Workers, Vercel Edge, any fetch-enabled runtime): https://botwire.dev/articles/vercel-ai-sdk-memory
>
> If useful for your docs' "Memory & State" section, I'd love for you to link it. Alternatively, I could submit to your community showcase.
>
> — Pedro, MIT licensed, no pitch

---

## 5. Replit Agents team

**To:** hello@replit.com
**Subject:** `Fix for Replit agents losing state between runs`

> Hi Replit team,
>
> I built a 2-line persistent memory primitive that solves a common Replit agent pain: state vanishing when the Repl wakes up. `pip install botwire` — works inside any Repl.
>
> Wrote a guide specifically for Replit devs: https://botwire.dev/articles/replit-agents-memory
>
> Happy to be included in any community templates or docs. MIT, no strings.
>
> — Pedro

---

## 6. Supabase team

**To:** partnerships@supabase.com
**Subject:** `Agent-friendly memory layer built on top of Postgres (eventually)`

> Hi Supabase team,
>
> I built a free persistent memory primitive for AI agents. Currently SQLite-backed but the data model is pg-compatible and I'd love to offer a Supabase-hosted deployment option eventually.
>
> Curious if you'd be interested in featuring this in your AI/agents section once the Supabase backend is ready, or if there's a partnership model for integrations.
>
> Current: https://botwire.dev | Source: MIT
>
> — Pedro

---

## 7. Modal.com

**To:** hello@modal.com
**Subject:** `Persistent memory for Modal-hosted AI agents`

> Hi Modal team,
>
> I wrote a guide specifically for Modal users running AI agents on ephemeral containers who need cross-run state: https://botwire.dev/articles/modal-ai-agent-memory
>
> Would love for it to live in your examples or ecosystem docs.
>
> — Pedro

---

## 8. Pydantic AI

**To:** Via GitHub issue on pydantic-ai repo — they prefer it
**Subject:** `Memory adapter for Pydantic AI agents`

> Hi Samuel & team,
>
> I built a persistent memory layer (`pip install botwire`) that works as a tool or external state store for Pydantic AI agents. Guide: https://botwire.dev/articles/pydantic-ai-memory
>
> Would love to be listed in your ecosystem or examples. Happy to PR if there's a good fit.
>
> — Pedro

---

## 9. Cloudflare Workers AI

**To:** workers-ai@cloudflare.com
**Subject:** `Persistent memory for Workers AI agents (edge-compatible)`

> Hi Cloudflare team,
>
> I built a memory API that's edge-compatible (fetch-only, no native deps). Runs great inside Workers. Guide: https://botwire.dev/articles/serverless-ai-agent-state
>
> Would love to be featured in any Workers AI example or tutorial that involves persistent agent state.
>
> — Pedro

---

## 10. Helicone / Langfuse / Portkey

**To:** (their respective contact emails)
**Subject:** `BotWire + [YourProduct] integration guide — listing request`

> Hi [team],
>
> I wrote a guide on pairing [YourProduct] observability with BotWire persistent memory: https://botwire.dev/articles/[your-slug]-plus-memory
>
> Would love for this to be linked from your integrations or docs — we're complementary (state + traces), not competitive.
>
> — Pedro

---

## Cadence
- Send 2-3/week. Don't blast 10 in one day — looks spammy.
- Track responses in a simple spreadsheet: Company | Sent | Response | Next step
- If no response in 10 days, one polite follow-up: "Bumping this in case it got buried."
- If no response in 20 days, move on.

## What success looks like
- 3 of 10 respond positively
- 1 of 10 gives you a backlink in their docs
- That one backlink > 100 self-written guides for domain authority

## Batch 2 targets (when ready)
- Inngest, Temporal, E2B, Browserbase, Arize, Humanloop, Braintrust, Mastra, Agno, AgentOps
