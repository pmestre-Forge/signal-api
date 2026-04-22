"""Extract marketing/growth/sales responses and synthesize a demand-creation playbook."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

HERE = Path(__file__).parent
load_dotenv(HERE.parent.parent / "bot" / ".env", override=True)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

data = json.loads((HERE / "reports" / "raw_audits.json").read_text())

DEMAND_ROLES = {
    "devrel_jr", "devrel_sr",
    "marketing_copy", "marketing_growth", "marketing_seo",
    "marketing_content", "marketing_brand", "marketing_director",
    "cmo", "press", "partnerships",
    "sales_sdr", "sales_ae", "sales_director", "vp_sales",
    "pm_integrations", "community_manager",
}

demand = [a for a in data if a["persona_id"] in DEMAND_ROLES]
print(f"Found {len(demand)} demand-side audits")

lines = [f"[{a['product_name']}] {a['persona_title']}: {a['response']}" for a in demand]

prompt = f"""You are the CMO. Below are {len(demand)} responses from marketing, growth, devrel, sales, and partnerships people — each reacting to a specific BotWire product with zero traction.

Synthesize into a DEMAND CREATION PLAYBOOK. Be concrete. No fluff.

RAW DEMAND-SIDE AUDITS:
{chr(10).join(lines)}

Output this structure in markdown:

# BotWire Demand Creation Playbook

## The honest read on demand
[2-3 sentences: is there latent demand that good marketing could unlock, or is this pushing rope?]

## The one product with the most demand-creation potential
[which of the 7, and why — cite specific roles]

## The 5 concrete growth plays (ranked by ROI)
For each: Name, Channel, Audience, Message, Expected outcome, Cost.

## The 3 partnerships that would matter
[Name them. Why. Who to contact.]

## The content plan: 10 pieces of content that would drive signups
[Numbered list. Title + one-line description + where it lives.]

## The positioning shift that fixes everything (if any)
[Can repositioning alone unlock demand? What's the new tagline?]

## The demo that wins
[One specific live demo that would convert.]

## The honest verdict: can marketing save this?
[Yes/No/Partially. Why.]
"""

print("Synthesizing demand playbook (Sonnet)...")
msg = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    messages=[{"role": "user", "content": prompt}],
)
out = msg.content[0].text.strip()

report_path = HERE / "reports" / "DEMAND_PLAYBOOK.md"
report_path.write_text(out, encoding="utf-8")
print(f"Wrote {report_path}")
print("\n" + "="*60)
print(out)
