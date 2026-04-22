"""
Synthesize 728 audits into a CEO-level report.
Groups by product, highlights themes, surfaces dissent, ranks verdicts.
"""
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

HERE = Path(__file__).parent
load_dotenv(HERE.parent.parent / "bot" / ".env", override=True)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

data = json.loads((HERE / "reports" / "raw_audits.json").read_text())

# Group by product
by_product = defaultdict(list)
for r in data:
    by_product[r["product_id"]].append(r)


def synthesize_product(pid: str, audits: list) -> str:
    # Build compact input
    lines = []
    for a in audits:
        lines.append(f"[{a['tier']}] {a['persona_title']}: {a['response']}")
    audit_text = "\n".join(lines)

    prompt = f"""You are the Chief of Staff to the CEO. 104 employees across every role (janitor to board member) just audited this product. Below are their raw responses. Synthesize into a brutally honest executive summary.

PRODUCT: {audits[0]['product_name']}

RAW AUDITS ({len(audits)} responses):
{audit_text}

Output format:
## {audits[0]['product_name']}

**Verdict (one line):** [KILL / PIVOT / INVEST / HOLD]

**What's working (2 bullets max):**
- ...
- ...

**What's broken (3 bullets max):**
- ...
- ...
- ...

**Recurring themes across roles:**
- [theme]: cited by [which roles]

**Most damning quote:** "..." — [role]

**Most bullish quote:** "..." — [role]

**Recommended action this week (1 concrete thing):**
...

Be sharp, concrete, no corporate hedging. Cite specific roles when useful.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def build_ceo_cover(product_summaries: dict) -> str:
    summaries = "\n\n".join(f"### {pid}\n{s}" for pid, s in product_summaries.items())
    prompt = f"""You synthesized 728 audits across 7 products. Write the CEO cover memo — 1 page — top of report. Pedro is the solo founder/CEO.

Structure:
# BotWire — Audit Legion Report
*104 personas, 7 products, 728 audits, all in under 3 minutes.*

## One-paragraph verdict on the business
[brutally honest: what's the real story? is this a business or a portfolio of demos?]

## Product rankings (by KEEP/PIVOT/KILL)
| Product | Verdict | Why |
|---|---|---|

## The 3 things that must change this week
1. ...
2. ...
3. ...

## The uncomfortable truth
[one paragraph Pedro doesn't want to hear but needs to]

Here are the 7 product syntheses:

{summaries}
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


print("Synthesizing each product...")
product_syntheses = {}
for pid in ["signals", "memory", "identity", "logs", "notifications", "config", "dm"]:
    print(f"  {pid}...")
    product_syntheses[pid] = synthesize_product(pid, by_product[pid])

print("Writing CEO cover memo...")
cover = build_ceo_cover(product_syntheses)

report_path = HERE / "reports" / "CEO_REPORT.md"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(cover)
    f.write("\n\n---\n\n# Per-Product Deep Dives\n\n")
    for pid, s in product_syntheses.items():
        f.write(s + "\n\n---\n\n")

print(f"Wrote {report_path}")
