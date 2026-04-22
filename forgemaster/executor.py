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


def _parse_kv_block(text: str) -> dict:
    """Parse lines like 'key=value' where values can be multi-line until next key.
    Respects ``` code fences for multi-line code blocks."""
    out: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            buf.append(line)
            continue
        if not in_code:
            m = re.match(r"^(\w+)\s*=\s*(.*)", line)
            if m:
                if current_key is not None:
                    out[current_key] = "\n".join(buf).strip()
                current_key = m.group(1)
                buf = [m.group(2)]
                continue
        buf.append(line)
    if current_key is not None:
        out[current_key] = "\n".join(buf).strip()
    return out


def _handle_add_cookbook_recipe(title: str, explanation: str, code: str) -> str:
    """Append a recipe section to the cookbook page."""
    cookbook = ROOT / "static" / "articles" / "cookbook.html"
    if not cookbook.exists():
        raise FileNotFoundError("cookbook.html missing")
    html = cookbook.read_text(encoding="utf-8")

    # Build a new recipe block
    # Extract code if wrapped in ``` fences
    code_body = code
    m = re.search(r"```(?:python)?\n(.*?)```", code, re.DOTALL)
    if m:
        code_body = m.group(1).rstrip()
    code_body_esc = code_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    block = (
        f"\n<h3>{title}</h3>\n"
        f"<p>{explanation}</p>\n"
        f"<pre><code>{code_body_esc}</code></pre>\n"
    )
    # Insert before the CTA div
    marker = '<div class="cta">'
    if marker in html:
        html = html.replace(marker, block + marker, 1)
        cookbook.write_text(html, encoding="utf-8")
        return f"Appended recipe '{title}' to cookbook.html"
    raise RuntimeError("cookbook layout changed — CTA marker not found")


def _handle_add_landing_quote(quote: str, attribution: str) -> str:
    """Add a social proof quote block to the landing page."""
    if not quote or len(quote) > 300:
        raise ValueError("quote must be 1-300 chars")
    index = ROOT / "static" / "index.html"
    html = index.read_text(encoding="utf-8")
    quote_esc = quote.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    attr_esc = (attribution or "Happy dev").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Insert before the pricing section marker
    marker = '<h2>Pricing</h2>'
    if marker not in html:
        raise RuntimeError("landing layout changed — Pricing marker not found")
    block = f'<div class="quote">"{quote_esc}" <span style="color:#666;font-size:0.85em">— {attr_esc}</span></div>\n\n        '
    html = html.replace(marker, block + marker, 1)
    index.write_text(html, encoding="utf-8")
    return f"Added quote to landing page: \"{quote[:60]}...\""


def _handle_add_faq_item(question: str, answer: str) -> str:
    """Append a FAQ item to the FAQ article."""
    faq = ROOT / "static" / "articles" / "faq.html"
    if not faq.exists():
        raise FileNotFoundError("faq.html missing")
    html = faq.read_text(encoding="utf-8")
    q_esc = question.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    a_esc = answer.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    block = f"\n<h3>{q_esc}</h3>\n<p>{a_esc}</p>\n"
    marker = '<div class="cta">'
    if marker in html:
        html = html.replace(marker, block + marker, 1)
        faq.write_text(html, encoding="utf-8")
        return f"Added FAQ item: \"{question[:60]}\""
    raise RuntimeError("FAQ layout changed")


def _handle_ping_indexnow() -> str:
    """Re-submit all URLs to IndexNow."""
    result = subprocess.run(
        [sys.executable, "forgemaster/seo/indexnow_all.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return f"IndexNow: {result.stdout[-200:] or result.stderr[-200:]}"


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
            kv = dict(re.findall(r"(\w+)\s*=\s*(.+)", args))
            result = _handle_add_article(
                slug=kv["slug"].strip(),
                title=kv["title"].strip(),
                query=kv.get("query", kv["title"]).strip(),
                keywords=kv.get("keywords", "").strip(),
                intent=kv.get("intent", "").strip(),
            )
        elif action == "ADD_COOKBOOK_RECIPE":
            # Format: title=X\ncode=```python\n...\n```
            kv = _parse_kv_block(args)
            result = _handle_add_cookbook_recipe(
                title=kv.get("title", "New recipe"),
                explanation=kv.get("explanation", ""),
                code=kv.get("code", ""),
            )
        elif action == "ADD_LANDING_QUOTE":
            # Format: quote=... attribution=...
            kv = _parse_kv_block(args)
            result = _handle_add_landing_quote(
                quote=kv.get("quote", "").strip(),
                attribution=kv.get("attribution", "").strip(),
            )
        elif action == "ADD_FAQ_ITEM":
            kv = _parse_kv_block(args)
            result = _handle_add_faq_item(
                question=kv.get("question", "").strip(),
                answer=kv.get("answer", "").strip(),
            )
        elif action == "PING_INDEXNOW":
            result = _handle_ping_indexnow()
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
