"""
Weekly retrospective agent.

Runs once a week (or on demand). Reads the last 7 days of proposals + platform
stats + new articles shipped + waitlist growth. Asks Claude to write an honest
retrospective: what worked, what didn't, patterns, recommendations for next week.

Output is saved as an article at /articles/retro-YYYY-MM-DD.html AND emailed
to Pedro in the next daily report.
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / "bot" / ".env", override=True)

sys.path.insert(0, str(Path(__file__).parent))
import proposals as prop_store
from audit_legion.audit_proposal import _platform_context

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

BASE = "https://botwire.dev"


def _j(path: str):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _gather() -> dict:
    now = int(time.time())
    week_ago = now - 7 * 24 * 3600

    all_props = prop_store.list_all()
    recent = [p for p in all_props if p.created_at >= week_ago]

    by_status: dict[str, int] = {}
    for p in all_props:
        by_status[p.status] = by_status.get(p.status, 0) + 1

    articles_dir = PROJECT_ROOT / "static" / "articles"
    articles = list(articles_dir.glob("*.html"))
    recent_articles = [
        {"slug": f.stem, "modified": int(f.stat().st_mtime)}
        for f in articles
        if f.stat().st_mtime >= week_ago
    ]

    return {
        "period": {"start": week_ago, "end": now},
        "stats": {
            "identity": _j("/stats/identity") or {},
            "memory": _j("/stats/memory") or {},
            "logs": _j("/stats/logs") or {},
            "waitlist": _j("/waitlist/stats") or {},
        },
        "proposals_week": [
            {
                "id": p.id,
                "title": p.title,
                "type": p.type,
                "proposer": p.proposer,
                "status": p.status,
                "legion_verdict": (p.legion_verdict or {}).get("verdict"),
                "ceo_decision": (p.ceo_decision or {}).get("decision"),
                "reasoning": (p.ceo_decision or {}).get("reasoning", "")[:200],
            }
            for p in recent
        ],
        "proposals_by_status": by_status,
        "articles_shipped_week": recent_articles,
        "total_articles": len(articles),
    }


def generate_retrospective() -> dict:
    data = _gather()

    prompt = f"""You are the acting Chief of Staff writing the weekly retrospective memo for the CEO (Pedro, solo founder of BotWire).

Write it with warmth and brutal honesty. Builder-to-builder. Cite specific proposal IDs. Be critical when warranted.

LAST 7 DAYS OF PLATFORM DATA:
{json.dumps(data, indent=2, default=str)}

PLATFORM CONTEXT:
{_platform_context()}

Structure the retrospective as markdown:

## The number that matters this week
(waitlist signups? new articles? registered agents? pick the ONE metric that tells the real story, and say whether it moved enough)

## What worked
- 2-4 bullets. Cite proposal IDs, decisions, or concrete shipped things.

## What didn't
- 2-4 bullets. Be honest — empty platform, no users, etc.

## Patterns I'm noticing
1-3 sentences about what the data tells us about the strategy.

## Next week — proposed focus
3 concrete things to do. Each one bulleted.

## Honest gut check for Pedro
1-2 sentences. What would you tell him if you were brutally candid? Is he on track? Drifting?

500-700 words. Markdown only. No intro, start with the ## heading.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    body_md = msg.content[0].text.strip()

    # Save as article
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = f"retro-{today}"
    title = f"Weekly retrospective — {today}"

    sys.path.insert(0, str(Path(__file__).parent / "seo"))
    from generate_articles import markdown_to_html

    html_body = markdown_to_html(body_md)
    canonical = f"https://botwire.dev/articles/{slug}"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "url": canonical,
        "datePublished": today,
        "author": {"@type": "Organization", "name": "BotWire Forgemaster"},
    }

    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | BotWire</title>
<meta name="description" content="Weekly retrospective — what the platform learned, what shipped, what failed.">
<meta name="robots" content="noindex">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{json.dumps(jsonld)}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#d0d0d0;line-height:1.75;font-size:17px}}
nav{{padding:15px 20px;border-bottom:1px solid #222}} nav a{{color:#4CAF50;text-decoration:none;font-weight:600}}
.c{{max-width:720px;margin:0 auto;padding:40px 20px 80px}}
h1{{color:#fff;font-size:2em;margin-bottom:10px}}
.meta{{color:#888;margin-bottom:30px}}
h2{{color:#fff;font-size:1.35em;margin:30px 0 10px}}
h3{{color:#ddd;font-size:1.1em;margin:20px 0 8px}}
p{{margin-bottom:15px;color:#c5c5c5}}
ul,ol{{margin:0 0 18px 22px;color:#c5c5c5}}
li{{margin-bottom:7px}}
code{{background:#1a1a1a;padding:2px 6px;border-radius:4px;color:#f1fa8c}}
strong{{color:#eee}}
</style></head>
<body><nav><a href="/">&larr; BotWire</a> &middot; <a href="/governance">Governance</a></nav>
<div class="c">
<h1>{title}</h1>
<p class="meta">Autonomous retrospective by Forgemaster &middot; {today}</p>
{html_body}
</div></body></html>"""

    out = PROJECT_ROOT / "static" / "articles" / f"{slug}.html"
    out.write_text(html, encoding="utf-8")

    # Also append to sitemap
    sitemap = PROJECT_ROOT / "static" / "sitemap.xml"
    xml = sitemap.read_text(encoding="utf-8")
    new_url = f'  <url><loc>{canonical}</loc><changefreq>never</changefreq><priority>0.5</priority></url>'
    if slug not in xml:
        xml = xml.replace("</urlset>", new_url + "\n</urlset>")
        sitemap.write_text(xml, encoding="utf-8")

    return {"slug": slug, "path": str(out), "body_md": body_md, "title": title}


if __name__ == "__main__":
    r = generate_retrospective()
    print(f"Wrote {r['path']}")
    print("\n--- PREVIEW ---\n")
    print(r["body_md"][:800])
