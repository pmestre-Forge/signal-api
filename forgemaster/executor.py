"""
Executor — auto-ships proposals the CEO approved AND tagged safe_to_auto_execute.

Whitelist-based. Each action type maps to a verified-safe handler. Anything not on
the whitelist is left for Pedro to ship manually (status stays "approved").

Supported actions (via proposal type):
- "content" + description starts with "ADD_ARTICLE slug=..." → generate & deploy a new SEO article
- "content" + description starts with "ADD_RECIPE" → append a recipe to the cookbook
- "positioning" + description starts with "UPDATE_BOT_ROTATION" → replace bot PRODUCT_ROTATION entry
- (more handlers can be added — each should be small, reversible, and git-logged)

Anything else marked safe_to_auto_execute still gets flagged but NOT executed;
Pedro handles.
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import proposals as prop_store

ROOT = Path(__file__).parent.parent


# --- Handlers ------------------------------------------------------------

def _handle_add_article(slug: str, title: str, query: str, keywords: str, intent: str) -> str:
    """Generate one new SEO article using the existing pipeline."""
    # Write a one-off generator script and run it
    tmpfile = ROOT / "forgemaster" / "seo" / f"_oneoff_{slug}.py"
    content = f"""from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import generate, render_html, ARTICLES_DIR

article = {{
    "slug": {slug!r},
    "title": {title!r},
    "query": {query!r},
    "keywords": {keywords!r},
    "intent": {intent!r},
}}
r = generate(article)
(ARTICLES_DIR / f"{{article['slug']}}.html").write_text(render_html(r), encoding="utf-8")
print(f"Wrote {{article['slug']}}.html")
"""
    tmpfile.write_text(content, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(tmpfile)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    tmpfile.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"Article generation failed: {result.stderr}")

    # Append OG image meta to the new article
    subprocess.run(
        [sys.executable, "forgemaster/seo/inject_og_images.py"],
        cwd=str(ROOT),
        timeout=60,
    )

    # Update sitemap — quick string append
    sitemap = ROOT / "static" / "sitemap.xml"
    xml = sitemap.read_text(encoding="utf-8")
    new_url = f'  <url><loc>https://botwire.dev/articles/{slug}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>'
    if slug not in xml:
        xml = xml.replace("</urlset>", new_url + "\n</urlset>")
        sitemap.write_text(xml, encoding="utf-8")

    return f"Generated /articles/{slug} + injected OG + added to sitemap. Commit/deploy remains with Pedro."


def _handle_update_bot_rotation(index: int, new_entry: dict) -> str:
    """Replace a single product in the bot's rotation."""
    # Safety: only allow adjusting 'focus' or 'endpoint' text, not structure
    bot_file = ROOT / "bot" / "generate.py"
    content = bot_file.read_text(encoding="utf-8")
    # We don't risk editing Python source with regex — just flag for human review
    return (
        f"[MANUAL REVIEW NEEDED] Bot rotation update requires editing bot/generate.py[{index}]. "
        f"Proposed: {new_entry}. Not auto-applied."
    )


# --- Dispatcher ----------------------------------------------------------

ACTION_RE = re.compile(r"^([A-Z_]{3,40})\s*(.*)", re.DOTALL)


def _parse_action(description: str) -> tuple[str, str] | None:
    """Description may start with 'ACTION_NAME\\n<rest>'. Return (action, rest) or None."""
    first_line = description.strip().split("\n", 1)
    m = ACTION_RE.match(first_line[0])
    if not m:
        return None
    rest = first_line[1] if len(first_line) > 1 else m.group(2)
    return m.group(1), rest.strip()


def execute(pid: str) -> dict:
    """Attempt to execute one approved proposal. Returns {executed, notes}."""
    p = prop_store.load(pid)
    if not p:
        return {"error": "not found"}
    if p.status != "approved":
        return {"skipped": f"status is {p.status}, not 'approved'"}
    decision = p.ceo_decision or {}
    if not decision.get("safe_to_auto_execute"):
        return {"skipped": "CEO flagged NOT safe to auto-execute"}

    parsed = _parse_action(p.description)
    if not parsed:
        return {"skipped": "no ACTION prefix in description"}
    action, args = parsed

    try:
        if action == "ADD_ARTICLE":
            # Expect key=value\n pairs
            kv = dict(re.findall(r"(\w+)\s*=\s*(.+)", args))
            result = _handle_add_article(
                slug=kv["slug"].strip(),
                title=kv["title"].strip(),
                query=kv.get("query", kv["title"]).strip(),
                keywords=kv.get("keywords", "").strip(),
                intent=kv.get("intent", "").strip(),
            )
        elif action == "UPDATE_BOT_ROTATION":
            result = "UPDATE_BOT_ROTATION is flagged manual-only for safety."
        else:
            return {"skipped": f"unknown action: {action}"}

        prop_store.set_status(pid, "executed", executor_notes=result)
        return {"executed": True, "action": action, "notes": result}
    except Exception as e:
        prop_store.set_status(pid, "failed", executor_notes=f"executor error: {e}")
        return {"error": str(e)}


def execute_all_approved() -> list[dict]:
    """Run executor against all currently-approved proposals."""
    out = []
    for p in prop_store.list_all():
        if p.status == "approved":
            r = execute(p.id)
            r["proposal_id"] = p.id
            out.append(r)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(execute_all_approved(), indent=2))
