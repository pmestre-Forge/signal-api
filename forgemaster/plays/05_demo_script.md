# Live Demo — "Your Agent Forgets. Here's the Fix."

**Target length:** 90 seconds. Loop-able. Shareable on Twitter/LinkedIn.

**Hook (first 3 seconds):**
> "Watch this AI agent forget who I am. Then watch it remember."

---

## Scene 1 — The Problem (30s)

**Screen:** Terminal, left half. Simple chat agent code, right half.

```python
# agent_no_memory.py
import anthropic
client = anthropic.Anthropic()

def chat(user_msg):
    resp = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": user_msg}],
    )
    return resp.content[0].text
```

**Action:** Run it twice.

```
$ python agent_no_memory.py
> My name is Pedro and I'm building an AI trading bot.
Agent: Hi Pedro! That sounds exciting. What stocks are you looking at?

$ python agent_no_memory.py
> What's my name?
Agent: I don't have information about your name. Could you tell me?
```

**Voiceover/caption:**
> "Every script restart = total amnesia. Every tutorial hacks around this with file dumps, Redis setups, or in-memory buffers that vanish on exit."

---

## Scene 2 — The Fix (30s)

**Screen:** Same layout. Edit the code.

```python
# agent_with_memory.py
import anthropic
from botwire import Memory            # <-- ADD THIS

client = anthropic.Anthropic()
mem = Memory("pedro-demo")             # <-- ADD THIS

def chat(user_msg):
    history = mem.get("history", default=[])
    history.append({"role": "user", "content": user_msg})

    resp = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=200,
        messages=history,
    )
    reply = resp.content[0].text
    history.append({"role": "assistant", "content": reply})
    mem.set("history", history)        # <-- AND THIS
    return reply
```

**Voiceover:**
> "Three lines. No Redis. No Docker. No signup."

---

## Scene 3 — The Payoff (25s)

**Action:** Run it twice.

```
$ python agent_with_memory.py
> My name is Pedro and I'm building an AI trading bot.
Agent: Hi Pedro! That sounds exciting. What stocks are you looking at?

$ python agent_with_memory.py
> What's my name?
Agent: Your name is Pedro, and you're building an AI trading bot.
```

**Voiceover:**
> "Same script, different process — the agent remembers. That's it."

---

## Scene 4 — The CTA (5s)

**Screen:** Full-screen card.

```
botwire.dev
pip install botwire
```

**Voiceover (or text):**
> "Free tier. MIT. Stop gluing Redis into every agent."

---

## Production notes
- **Use `asciinema` or `vhs`** (by charmbracelet) for the terminal recordings — crisper than screen recording and exports to GIF/MP4.
- **vhs tape script:** save as `demo.tape`:

```
Output demo.gif
Set FontSize 18
Set Width 1200
Set Height 700

Type "python agent_no_memory.py"
Enter
Sleep 500ms
Type "My name is Pedro..."
Enter
Sleep 1s
# ... etc
```

- **No background music** for Twitter. Silence is better for autoplay-muted feeds.
- **Captions burned-in** — 80%+ of autoplay views are muted.
- **Aspect ratio:** 1:1 for Twitter, 9:16 for TikTok/Shorts variant.
- **Thumbnail:** the "Agent: I don't have information about your name" frame — that's the ouch moment.

## Distribution
- Twitter post: `"your agent forgets. here's the fix. [GIF] botwire.dev"`
- LinkedIn: longer caption with "I built this because…" story
- Dev.to: embed GIF in article with code
- YouTube Shorts: vertical version, same content
- HN front page: embed the GIF as the top of the Show HN post
