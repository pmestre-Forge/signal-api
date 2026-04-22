"""Generate a cookbook page: 20 copy-paste recipes using BotWire."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / "bot" / ".env", override=True)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

OUT = ROOT / "static" / "articles" / "cookbook.html"

prompt = """Write a BotWire Memory Cookbook — 20 copy-paste recipes for common patterns. Each recipe is:
- H3 heading (### 1. Title)
- 1-sentence explanation of when you'd use it
- One working Python code block using `from botwire import Memory` (or BotWireChatHistory for LangChain cases)

Cover these patterns (invent concrete titles, keep them SEO-friendly):

1. Remember a user's name across sessions
2. Cache expensive LLM responses (idempotent memoization)
3. Per-user conversation history (LangChain)
4. Agent-to-agent coordination state
5. Counter that persists (increment across runs)
6. Feature flag store for agents
7. Last-seen timestamp tracker
8. Rate-limit counter (self-imposed)
9. Agent todo list persistence
10. Store API credentials namespace (with caveat)
11. Store user preferences dict
12. Multi-step workflow checkpoint
13. A/B test variant assignment
14. Seen-before deduplication set
15. Conversation summary rolling buffer
16. Cross-agent shared scratchpad
17. Per-session temp memory with TTL pattern
18. Export/import memory as JSON backup
19. Migrating existing Redis keys to BotWire
20. Using BotWire with Claude's tool-use / function-calling

Rules:
- Every snippet must work. No invented methods. Only use: Memory(ns), .set, .get(key, default=None), .delete, .keys, BotWireChatHistory(session_id=)
- Write realistic code (imports, full function signatures), not snippets that cut corners
- No framework for patterns 1-2 and 5-19 — plain Python
- Pattern 3: LangChain. Pattern 20: Claude Messages API via anthropic package.
- 20-40 lines of code per recipe max
- Don't repeat the same variable name `mem` across every recipe — vary namespaces

Output as markdown body only. Start with ## Cookbook. Short intro paragraph. Then the 20 recipes. End with a line linking back to pip install botwire.
"""

msg = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    messages=[{"role": "user", "content": prompt}],
)
body_md = msg.content[0].text.strip()
print(f"Generated {len(body_md)} chars")

# Reuse the same renderer
import sys
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import markdown_to_html

html_body = markdown_to_html(body_md)

title = "BotWire Memory Cookbook: 20 Copy-Paste Recipes"
description = "20 copy-paste code recipes for persistent memory in AI agents. User prefs, caching, checkpoints, rate limits, LangChain, Claude, and more."
canonical = "https://botwire.dev/articles/cookbook"

jsonld = {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": title,
    "description": description,
    "url": canonical,
    "datePublished": "2026-04-22",
    "dateModified": "2026-04-22",
    "author": {"@type": "Organization", "name": "BotWire"},
    "publisher": {"@type": "Organization", "name": "BotWire"},
    "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    "keywords": "botwire cookbook, ai agent memory recipes, langchain memory recipe, persistent memory examples, botwire examples",
}

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | BotWire</title>
<meta name="description" content="{description}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<script type="application/ld+json">{json.dumps(jsonld)}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#d0d0d0;line-height:1.7;font-size:17px}}
.c{{max-width:800px;margin:0 auto;padding:40px 20px 80px}}
nav{{padding:15px 20px;border-bottom:1px solid #222}}
nav a{{color:#4CAF50;text-decoration:none;font-weight:600}}
h1{{color:#fff;font-size:2.3em;line-height:1.2;margin-bottom:15px}}
.lede{{color:#888;margin-bottom:30px}}
h2{{color:#fff;font-size:1.5em;margin:40px 0 12px}}
h3{{color:#4CAF50;font-size:1.2em;margin:35px 0 10px;padding-top:25px;border-top:1px solid #222}}
h3:first-of-type{{border-top:none;padding-top:0}}
p{{margin:0 0 15px;color:#c5c5c5}}
code{{background:#1a1a1a;padding:2px 6px;border-radius:4px;color:#f1fa8c;border:1px solid #222;font-size:0.92em}}
pre{{background:#141414;border:1px solid #262626;border-radius:10px;padding:20px;overflow-x:auto;margin:15px 0}}
pre code{{background:transparent;padding:0;border:none;color:#e0e0e0;white-space:pre}}
.cta{{background:#1a3a1a;border:1px solid #4CAF50;border-radius:10px;padding:25px;margin:40px 0;text-align:center}}
.cta a{{color:#4CAF50;font-weight:600}}
</style>
</head>
<body>
<nav><a href="/">&larr; BotWire</a> &middot; <a href="/articles/">All guides</a></nav>
<div class="c">
<h1>{title}</h1>
<p class="lede">Copy, paste, adapt. Every recipe is runnable Python.</p>
{html_body}
<div class="cta">
<p>Install: <code>pip install botwire</code></p>
<p style="margin-top:10px"><a href="https://botwire.dev">botwire.dev</a></p>
</div>
</div>
</body>
</html>"""

OUT.write_text(html, encoding="utf-8")
print(f"Wrote {OUT}")
