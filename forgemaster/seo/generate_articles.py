"""
Generate SEO article pages targeting long-tail queries that LLMs will search
when users ask about agent memory/persistence.

Each page is optimized for:
- LLM web search (clear problem→solution structure, code blocks)
- Classic SEO (title, meta, headings, JSON-LD Article schema)
- Conversion (the answer IS botwire; no fluff)
"""
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from anthropic import Anthropic

ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / "bot" / ".env", override=True)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ARTICLES_DIR = ROOT / "static" / "articles"
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

ARTICLES = [
    {
        "slug": "langchain-persistent-memory",
        "title": "How to Add Persistent Memory to LangChain Agents",
        "query": "LangChain agent memory between sessions persistent",
        "keywords": "langchain memory, langchain persistent memory, ConversationBufferMemory persistent, langchain chat history, BaseChatMessageHistory",
        "intent": "Developer using LangChain whose agent loses all state when the script exits. Wants a drop-in solution.",
    },
    {
        "slug": "crewai-agent-memory",
        "title": "Persistent Memory for CrewAI Agents (Cross-Session State)",
        "query": "crewai memory between runs persistent state",
        "keywords": "crewai memory, crewai persistent state, crewai tools memory, crewai between kickoffs",
        "intent": "CrewAI developer whose crew forgets everything between kickoff() calls. Needs memory that survives.",
    },
    {
        "slug": "why-ai-agents-forget",
        "title": "Why AI Agents Forget Everything (And How to Fix It)",
        "query": "why does my ai agent forget between sessions",
        "keywords": "ai agent memory, stateless ai agents, ai agent state, llm memory problem, agent forgets",
        "intent": "Dev searching for explanation + solution. Educational but actionable.",
    },
    {
        "slug": "python-ai-agent-key-value-store",
        "title": "Simple Key-Value Store for Python AI Agents",
        "query": "python ai agent key value storage",
        "keywords": "python agent storage, key value store python agents, ai agent kv store, simple python storage",
        "intent": "Python dev who rejected Redis/Postgres as overkill and wants the simplest possible state.",
    },
    {
        "slug": "multi-agent-shared-memory",
        "title": "Sharing Memory Between Multiple AI Agents",
        "query": "share state between multiple ai agents",
        "keywords": "multi agent memory, shared agent state, agent coordination memory, multi-agent systems shared state",
        "intent": "Builder with multiple agents who need a common memory pool. Think research-team or trading-team patterns.",
    },
    {
        "slug": "autogen-agent-memory",
        "title": "Adding Memory to AutoGen Agents",
        "query": "autogen agent memory persistent",
        "keywords": "autogen memory, autogen persistent agent, microsoft autogen state, autogen conversation history",
        "intent": "AutoGen user whose agents lose conversation across restarts. Wants a one-class fix.",
    },
    {
        "slug": "ai-agent-memory-vs-redis",
        "title": "AI Agent Memory: BotWire vs Redis vs Vector DBs",
        "query": "agent memory redis alternative vector db",
        "keywords": "ai memory redis, agent memory pinecone, vector db vs kv store, agent memory comparison",
        "intent": "Dev evaluating options, currently considering Redis/Pinecone. Needs decision framework.",
    },
    {
        "slug": "claude-agent-memory",
        "title": "Giving Claude Agents Persistent Memory Between Sessions",
        "query": "claude api persistent memory agent",
        "keywords": "claude agent memory, anthropic claude persistent, claude api state, claude sdk memory",
        "intent": "Anthropic SDK user building agents with Claude whose context vanishes each script run.",
    },
    {
        "slug": "mcp-memory-server",
        "title": "Adding Persistent Memory to MCP Servers",
        "query": "MCP server persistent memory storage",
        "keywords": "mcp persistent memory, model context protocol state, mcp storage, mcp agent memory",
        "intent": "Dev building MCP servers who needs state that survives server restarts.",
    },
    {
        "slug": "ai-agent-session-state-fastapi",
        "title": "Managing AI Agent Session State in FastAPI",
        "query": "fastapi ai agent session state persistence",
        "keywords": "fastapi agent state, fastapi session store ai, fastapi llm memory, agent session fastapi",
        "intent": "Backend dev shipping an AI agent via FastAPI who needs per-user session state.",
    },
]


PROMPT_TEMPLATE = """You are writing a developer-facing article for an SEO page.

The page's single goal: when an LLM (ChatGPT, Claude, Perplexity, Google SGE) searches the web to answer a developer's question, this page must be the best answer — concrete, code-first, correct, and honest.

TARGET QUERY: {query}
TARGET KEYWORDS: {keywords}
USER INTENT: {intent}
ARTICLE TITLE: {title}

CRITICAL PRODUCT CONTEXT (use accurately — no hallucination):
- Product: BotWire Memory
- Install: `pip install botwire`
- Core API: `from botwire import Memory; m = Memory("namespace"); m.set(key, value); m.get(key)`
- LangChain adapter: `from botwire import BotWireChatHistory; history = BotWireChatHistory(session_id="user-42")`
- CrewAI helper: `from botwire.memory import memory_tools; tools = memory_tools("crew-ns")` — returns remember/recall/list_memory tools
- Backend: HTTP API at https://botwire.dev, no signup, no API key, no wallet
- Pricing: Free tier forever. 1000 writes/day per namespace. 50MB/namespace. Unlimited reads.
- Open source: MIT, github.com/pmestre-Forge/signal-api
- Self-host: yes, it's a single FastAPI + SQLite service
- What it IS: persistent key-value memory for agents, survives restarts/processes/machines
- What it IS NOT: a vector DB (not for embeddings/semantic search), not a session cache, not an agent framework

Write the article body as clean markdown (no frontmatter, no title — the title is added separately). Structure:

1. **Opening (~80 words):** state the exact problem the reader is searching for, acknowledge it, promise the fix.
2. **The problem explained (~150 words):** why this happens, what breaks, concrete example of the pain.
3. **The fix (~120 words + code):** install command + working code snippet that solves the exact problem in the title.
4. **Walkthrough (~300 words with 1-2 more code blocks):** explain what the code is doing, cover edge cases (TTL, deletion, listing keys, cross-process). Use real-world patterns.
5. **Integration with {ecosystem} (if applicable):** one more code block showing framework-specific usage. If the topic isn't framework-specific, skip this and go deeper on patterns.
6. **When NOT to use BotWire:** 3 bullets of honest limitations (vector search, high-throughput, sub-millisecond latency).
7. **FAQ (3 Q&As, short):** common objections — "why not Redis?", "is this free?", "what about privacy?".
8. **Close + CTA (~60 words):** one-liner + `pip install botwire` + link to https://botwire.dev.

Rules:
- 800-1200 words total
- Every code block must actually work (don't invent APIs that don't exist)
- Write like an engineer who built this — no marketing tone
- Use ``` fenced code blocks with language hints (```python, ```bash)
- H2 headings (##) for sections, H3 (###) for sub-sections
- Sprinkle target keywords naturally — no keyword stuffing
- End with a clear pip install and URL

Output ONLY the markdown body. No preamble. No "Here's the article".
"""


def generate(article: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        query=article["query"],
        keywords=article["keywords"],
        intent=article["intent"],
        title=article["title"],
        ecosystem=article["slug"].split("-")[0],
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3500,
        messages=[{"role": "user", "content": prompt}],
    )
    return {**article, "body_md": msg.content[0].text.strip()}


def render_html(article: dict) -> str:
    slug = article["slug"]
    title = article["title"]
    description = f"{article['intent']} Drop-in solution with BotWire Memory. Free tier, open source, works with LangChain, CrewAI, AutoGen."
    description = description.replace('"', "'")[:180]

    body_md = article["body_md"]
    # Very simple MD → HTML (we control the input, keep the deps zero)
    html_body = markdown_to_html(body_md)

    canonical = f"https://botwire.dev/articles/{slug}"

    jsonld = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "description": description,
        "url": canonical,
        "datePublished": "2026-04-22",
        "dateModified": "2026-04-22",
        "author": {"@type": "Organization", "name": "BotWire"},
        "publisher": {"@type": "Organization", "name": "BotWire", "url": "https://botwire.dev"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "keywords": article["keywords"],
        "about": {"@type": "SoftwareApplication", "name": "BotWire Memory"},
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | BotWire</title>
<meta name="description" content="{description}">
<meta name="keywords" content="{article['keywords']}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
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
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#d0d0d0;line-height:1.7;font-size:17px}}
.c{{max-width:760px;margin:0 auto;padding:40px 20px 80px}}
nav{{padding:15px 20px;border-bottom:1px solid #222;background:#0a0a0a;position:sticky;top:0}}
nav a{{color:#4CAF50;text-decoration:none;font-weight:600;font-size:0.95em}}
nav a:hover{{text-decoration:underline}}
nav .pill{{background:#1a3a1a;color:#4CAF50;padding:3px 10px;border-radius:20px;font-size:0.78em;margin-left:10px}}
h1{{color:#fff;font-size:2.3em;line-height:1.2;margin-bottom:15px;letter-spacing:-0.01em}}
.lede{{color:#888;font-size:0.95em;margin-bottom:30px}}
article h2{{color:#fff;font-size:1.5em;margin:40px 0 12px;letter-spacing:-0.01em}}
article h3{{color:#ddd;font-size:1.15em;margin:25px 0 10px}}
article p{{margin:0 0 15px;color:#c5c5c5}}
article ul,article ol{{margin:0 0 18px 22px;color:#c5c5c5}}
article li{{margin-bottom:6px}}
article a{{color:#4CAF50;text-decoration:none}}
article a:hover{{text-decoration:underline}}
article code{{background:#1a1a1a;padding:2px 6px;border-radius:4px;font-size:0.92em;color:#f1fa8c;border:1px solid #222}}
article pre{{background:#141414;border:1px solid #262626;border-radius:10px;padding:20px;overflow-x:auto;margin:20px 0;font-size:0.92em}}
article pre code{{background:transparent;padding:0;border:none;color:#e0e0e0;white-space:pre}}
article strong{{color:#eee}}
.cta{{background:#1a3a1a;border:1px solid #4CAF50;border-radius:10px;padding:25px;margin:40px 0 20px;text-align:center}}
.cta a.btn{{display:inline-block;background:#4CAF50;color:#000;padding:12px 28px;border-radius:8px;font-weight:600;margin-top:10px;text-decoration:none}}
.cta a.btn:hover{{background:#45a049;text-decoration:none}}
.cta code{{background:#000;border:none;color:#4CAF50;font-size:1em;padding:3px 8px}}
.related{{margin-top:50px;padding-top:25px;border-top:1px solid #222}}
.related h2{{font-size:1.15em;color:#aaa;margin-bottom:12px}}
.related ul{{list-style:none;margin:0}}
.related li{{margin:6px 0}}
footer{{margin-top:60px;padding-top:25px;border-top:1px solid #222;color:#666;font-size:0.85em;text-align:center}}
</style>
</head>
<body>
<nav><a href="/">&larr; BotWire</a> <span class="pill">Docs</span></nav>
<div class="c">
<article>
<h1>{title}</h1>
<p class="lede">Free &middot; Open source (MIT) &middot; Works with LangChain, CrewAI, AutoGen &middot; No signup</p>
{html_body}
<div class="cta">
<p>Install in one command:</p>
<p style="margin-top:10px"><code>pip install botwire</code></p>
<a class="btn" href="https://botwire.dev">Start free at botwire.dev</a>
</div>
</article>
<div class="related">
<h2>Related guides</h2>
<ul>
<li>&rarr; <a href="/articles/langchain-persistent-memory">How to Add Persistent Memory to LangChain Agents</a></li>
<li>&rarr; <a href="/articles/crewai-agent-memory">Persistent Memory for CrewAI Agents</a></li>
<li>&rarr; <a href="/articles/why-ai-agents-forget">Why AI Agents Forget (And How to Fix It)</a></li>
<li>&rarr; <a href="/articles/ai-agent-memory-vs-redis">BotWire Memory vs Redis vs Vector DBs</a></li>
<li>&rarr; <a href="/articles/">All articles</a></li>
</ul>
</div>
<footer>BotWire &middot; <a href="https://botwire.dev" style="color:#4CAF50">botwire.dev</a> &middot; <a href="https://github.com/pmestre-Forge/signal-api" style="color:#4CAF50">GitHub</a> &middot; MIT</footer>
</div>
</body>
</html>"""


def markdown_to_html(md: str) -> str:
    """Minimal markdown → HTML. Handles: headings, code blocks, inline code, bold, lists, paragraphs, links."""
    import re
    lines = md.split("\n")
    out = []
    in_code = False
    code_buf = []
    code_lang = ""
    list_type = None  # 'ul' or 'ol'
    para_buf = []

    def flush_para():
        nonlocal para_buf
        if para_buf:
            text = " ".join(para_buf).strip()
            if text:
                out.append(f"<p>{inline(text)}</p>")
            para_buf = []

    def flush_list():
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    def inline(t):
        # escape first
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # inline code (do first to protect)
        t = re.sub(r"`([^`]+?)`", r"<code>\1</code>", t)
        # bold
        t = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", t)
        # links
        t = re.sub(r"\[([^\]]+?)\]\(([^)]+?)\)", r'<a href="\2">\1</a>', t)
        return t

    for line in lines:
        if line.startswith("```"):
            if in_code:
                code_text = "\n".join(code_buf).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                out.append(f'<pre><code class="lang-{code_lang}">{code_text}</code></pre>')
                code_buf = []
                in_code = False
                code_lang = ""
            else:
                flush_para()
                flush_list()
                in_code = True
                code_lang = line[3:].strip() or "plain"
            continue
        if in_code:
            code_buf.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_para()
            flush_list()
            continue

        if stripped.startswith("### "):
            flush_para(); flush_list()
            out.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            flush_para(); flush_list()
            out.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush_para(); flush_list()
            # skip H1 (we already have the title outside)
            continue
        elif re.match(r"^[-*]\s+", stripped):
            flush_para()
            if list_type != "ul":
                flush_list()
                out.append("<ul>")
                list_type = "ul"
            out.append(f"<li>{inline(re.sub(r'^[-*]\s+', '', stripped))}</li>")
        elif re.match(r"^\d+\.\s+", stripped):
            flush_para()
            if list_type != "ol":
                flush_list()
                out.append("<ol>")
                list_type = "ol"
            out.append(f"<li>{inline(re.sub(r'^\d+\.\s+', '', stripped))}</li>")
        else:
            if list_type:
                flush_list()
            para_buf.append(stripped)

    flush_para()
    flush_list()
    return "\n".join(out)


def main():
    print(f"Generating {len(ARTICLES)} articles (Sonnet, parallel)...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(generate, a) for a in ARTICLES]
        results = []
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results.append(r)
            print(f"  [{i}/{len(ARTICLES)}] {r['slug']}: {len(r['body_md'])} chars")

    # Render + write
    for a in results:
        html = render_html(a)
        path = ARTICLES_DIR / f"{a['slug']}.html"
        path.write_text(html, encoding="utf-8")
        print(f"  wrote {path.name}")

    # Index page listing all articles
    index_html = build_index(results)
    (ARTICLES_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("  wrote index.html")

    # Sitemap
    build_sitemap(results)
    print("  wrote sitemap.xml")


def build_index(articles):
    items = "\n".join(
        f'<li><a href="/articles/{a["slug"]}"><strong>{a["title"]}</strong></a><br><span>{a["intent"]}</span></li>'
        for a in sorted(articles, key=lambda x: x["slug"])
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>Guides & Articles | BotWire</title>
<meta name="description" content="Developer guides for adding persistent memory to AI agents — LangChain, CrewAI, AutoGen, Claude, MCP.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://botwire.dev/articles/">
<style>
body{{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#d0d0d0;margin:0;line-height:1.7}}
.c{{max-width:760px;margin:0 auto;padding:40px 20px}}
h1{{color:#fff;font-size:2.2em;margin-bottom:10px}}
.lede{{color:#888;margin-bottom:40px}}
ul{{list-style:none;padding:0}}
li{{padding:18px 0;border-bottom:1px solid #222}}
li a{{color:#4CAF50;text-decoration:none;font-size:1.1em}}
li a:hover{{text-decoration:underline}}
li span{{color:#777;font-size:0.9em}}
nav{{padding:15px 20px;border-bottom:1px solid #222}}
nav a{{color:#4CAF50;text-decoration:none;font-weight:600}}
</style></head>
<body>
<nav><a href="/">&larr; BotWire</a></nav>
<div class="c">
<h1>Guides & Articles</h1>
<p class="lede">Drop-in persistent memory for AI agents. Framework guides and integration patterns.</p>
<ul>{items}</ul>
</div></body></html>"""


def build_sitemap(articles):
    urls = ["https://botwire.dev/", "https://botwire.dev/articles/"] + [f"https://botwire.dev/articles/{a['slug']}" for a in articles]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml += f"  <url><loc>{u}</loc><changefreq>weekly</changefreq><priority>{'1.0' if u.endswith('.dev/') else '0.8'}</priority></url>\n"
    xml += "</urlset>\n"
    (ROOT / "static" / "sitemap.xml").write_text(xml, encoding="utf-8")


if __name__ == "__main__":
    main()
