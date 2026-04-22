# Discord Infiltration — Per-Community Messages

**Rules of engagement:**
- Spend 3 days in each server BEFORE posting. Comment on other people's questions. Answer noob questions. Be human.
- DO NOT drop the link cold. Wait for the right thread.
- When someone asks "how do I persist X between agent runs" → that's your moment.
- If the first message gets deleted, you did it wrong. Don't repost.

---

## 1. LangChain Discord
**Channel:** `#general` or `#show-and-tell`
**Invite:** https://discord.gg/langchain (Pedro needs to join via his account)

**Reactive message (wait for someone to ask about memory/persistence):**

> Been hitting the same thing — LangChain's `ConversationBufferMemory` is great in-process but vanishes when your script ends. I built a drop-in HTTP layer that survives restarts:
>
> ```python
> from botwire import Memory
> mem = Memory(f"agent-{user_id}")
> mem.set("last_message", response)
> ```
>
> Works alongside LangChain's classes — I use it for "agent state that must outlive the process" and let LangChain handle the in-conversation buffer. Free tier is forever, MIT licensed.
>
> https://botwire.dev — happy to answer questions if anyone tries it.

**Proactive message (only after 3+ days of good-faith participation):**

> Quick one for the memory people here: if I wanted to share a single long-term memory across 5 parallel LangChain agents on different machines, what would you use today? Redis? Shared DB? I built a tiny HTTP thing for this (botwire.dev) but curious what patterns people are actually running.

---

## 2. CrewAI Discord
**Channel:** `#help` or `#showcase`
**Invite:** https://discord.gg/X4JWnZnxPb (or current CrewAI invite)

**Reactive message:**

> If the crew needs memory across runs (not just within a single `kickoff()`), I've been using a tiny HTTP memory API — works as a custom tool:
>
> ```python
> from crewai_tools import tool
> from botwire import Memory
>
> mem = Memory("research-crew")
>
> @tool("Remember fact")
> def remember(key: str, value: str) -> str:
>     mem.set(key, value)
>     return f"stored {key}"
>
> @tool("Recall fact")
> def recall(key: str) -> str:
>     return mem.get(key) or "not found"
> ```
>
> Drop those into any agent's tools list, now the crew has persistent memory across runs. Free tier: https://botwire.dev

---

## 3. AutoGPT / AutoGen Community
**Channel:** `#agent-development` or `#tools`
**Invite:** per community

**Message:**

> Shipped a simple persistent memory layer for agents — came out of my own pain. Key-value, HTTP, free tier, no infra:
>
> https://botwire.dev
>
> Works for cases where the agent needs to remember something between runs (user prefs, last actions, long-term goals). Paste-ready Python client.

---

## 4. Anthropic MCP Discord
**Channel:** `#general` or `#mcp-servers`
**Invite:** https://discord.gg/anthropic

**Message (more technical audience):**

> Hey — curious if anyone's built an MCP memory server yet. I've got an HTTP one that I could wrap as MCP in an afternoon (botwire.dev). Is there appetite, or does everyone already have their own?

**Follow-up if appetite exists:** ship the MCP wrapper as `botwire-mcp` within a week.

---

## 5. r/LocalLLaMA Discord (or subreddit)
**Channel:** `#self-hosted-tools`

**Message:**

> Built this because my local Llama agents kept forgetting everything between sessions. HTTP memory API, self-host or use free tier. MIT:
>
> https://botwire.dev
>
> Self-hosters: single FastAPI + SQLite file, `docker run` and you're good.

---

## Follow-up cadence
- After each message, pin a reminder to check for replies within 2h
- If 3+ people ask questions in a thread, **that thread IS the campaign** — spend a day answering
- Track responses in a spreadsheet: server, channel, date, engagement, signups traced via UTM

## UTM tags for tracking
Append `?utm_source=discord&utm_medium=<server>&utm_campaign=memory_launch` to any links.
