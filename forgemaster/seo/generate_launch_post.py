"""Generate a launch blog post — the pivot story."""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import markdown_to_html

ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / "bot" / ".env", override=True)
sys.path.insert(0, str(ROOT / "forgemaster"))
from llm import get_client
client = get_client()

prompt = """Write a personal, slightly self-deprecating engineering blog post. First-person voice as Pedro, the solo founder of BotWire.

Context:
- Built 7 services over ~2 weeks: trading signals, memory, identity, logs, notifications, config store, DMs. All agent-related.
- Got zero external users in the first 10 days.
- Ran a 728-persona audit (100 employee roles × 7 products) using Claude. Verdict on every product: KILL.
- The audit surfaced one real signal: Agent Memory is the only product solving a problem devs actually feel today. Rest are infrastructure for an agent economy that's 2 years early.
- Pivoted: made memory the headline, killed the micropayment paywall on writes (was $0.002), rewrote landing page, rebranded as "persistent memory for AI agents", shipped a Python SDK to PyPI, wrote 60+ SEO articles targeting long-tail queries from LangChain/CrewAI/Claude devs.
- Key decisions: don't delete the other products, but demote them. Payments on signals/world-context stay. Everything agent-facing goes free.
- Cost of the audit: $4 in Claude API. Cost of the 60 articles: ~$10.

Title: "I killed six of my own products this week"

Write 800-1100 words. Structure:
1. Hook (the "I killed six products" moment)
2. What I built, briefly and honestly
3. The audit — what 104 AI employees said
4. Reading the audit: the one product that wasn't noise
5. What changed this week: free memory, new site, 60 articles
6. Lessons — don't do what I did
7. What's next / how to try it

Tone: builder-to-builder, Paul Graham / Patrick McKenzie energy. No hype. Concrete numbers. One self-roast per 200 words allowed. Code blocks welcome. End with a single call to action: pip install botwire.

Markdown only. Start with ## sections, no H1.
"""

print("Generating launch blog post...")
msg = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    messages=[{"role": "user", "content": prompt}],
)
body_md = msg.content[0].text.strip()
print(f"Generated {len(body_md)} chars")

html_body = markdown_to_html(body_md)

title = "I killed six of my own products this week"
description = "A 728-persona audit told me to KILL everything. Here's what I kept, what I changed, and what I'd do differently. Solo founder post-mortem."
slug = "launch-post-i-killed-six-products"
canonical = f"https://botwire.dev/articles/{slug}"

jsonld = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": title,
    "description": description,
    "url": canonical,
    "datePublished": "2026-04-22",
    "dateModified": "2026-04-22",
    "author": {"@type": "Person", "name": "Pedro Mestre", "url": "https://github.com/pmestre-Forge"},
    "publisher": {"@type": "Organization", "name": "BotWire", "url": "https://botwire.dev"},
    "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    "image": f"https://botwire.dev/og/{slug}.svg",
}

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | BotWire</title>
<meta name="description" content="{description}">
<meta name="robots" content="index, follow, max-snippet:-1">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<meta property="og:image" content="https://botwire.dev/og/{slug}.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://botwire.dev/og/{slug}.svg">
<script type="application/ld+json">{json.dumps(jsonld)}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0a0a;color:#d0d0d0;line-height:1.75;font-size:18px}}
nav{{padding:15px 20px;border-bottom:1px solid #222}}
nav a{{color:#4CAF50;text-decoration:none;font-weight:600}}
.c{{max-width:680px;margin:0 auto;padding:40px 20px 80px}}
h1{{color:#fff;font-size:2.4em;line-height:1.15;margin-bottom:10px;letter-spacing:-0.02em}}
.meta{{color:#888;margin-bottom:40px;font-size:0.92em}}
article h2{{color:#fff;font-size:1.45em;margin:40px 0 14px;letter-spacing:-0.01em}}
article h3{{color:#ddd;font-size:1.15em;margin:25px 0 10px}}
article p{{margin:0 0 18px;color:#c5c5c5}}
article ul,article ol{{margin:0 0 20px 24px;color:#c5c5c5}}
article li{{margin-bottom:7px}}
article a{{color:#4CAF50;text-decoration:none;border-bottom:1px dashed #4CAF50}}
article a:hover{{border-bottom-style:solid}}
article code{{background:#1a1a1a;padding:2px 6px;border-radius:4px;font-size:0.92em;color:#f1fa8c;border:1px solid #222}}
article pre{{background:#141414;border:1px solid #262626;border-radius:10px;padding:20px;overflow-x:auto;margin:22px 0;font-size:0.92em}}
article pre code{{background:transparent;padding:0;border:none;color:#e0e0e0;white-space:pre}}
article strong{{color:#eee}}
.cta{{background:#1a3a1a;border:1px solid #4CAF50;border-radius:10px;padding:25px;margin:40px 0;text-align:center}}
footer{{margin-top:60px;padding-top:25px;border-top:1px solid #222;color:#666;font-size:0.85em;text-align:center}}
</style>
</head>
<body>
<nav><a href="/">&larr; BotWire</a> &middot; <a href="/articles/">All guides</a></nav>
<div class="c">
<article>
<h1>{title}</h1>
<p class="meta">Pedro Mestre &middot; April 22, 2026 &middot; Solo founder, BotWire</p>
{html_body}
<div class="cta">
<p style="font-size:1.15em;margin-bottom:8px"><strong>If the story resonates:</strong></p>
<p><code>pip install botwire</code></p>
<p style="margin-top:10px"><a href="https://botwire.dev" style="color:#4CAF50;font-weight:600">botwire.dev</a> &middot; <a href="/playground" style="color:#4CAF50">Try it live</a></p>
</div>
</article>
<footer>BotWire &middot; <a href="https://github.com/pmestre-Forge/signal-api" style="color:#4CAF50">GitHub</a></footer>
</div>
</body>
</html>"""

out = ROOT / "static" / "articles" / f"{slug}.html"
out.write_text(html, encoding="utf-8")
print(f"Wrote {out}")
