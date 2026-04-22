"""Batch 3: Competitor comparisons + framework quickstarts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import generate, render_html, ARTICLES_DIR, build_index, build_sitemap
from concurrent.futures import ThreadPoolExecutor, as_completed

BATCH3 = [
    {
        "slug": "botwire-vs-mem0",
        "title": "BotWire vs Mem0: Picking the Right AI Memory Tool",
        "query": "mem0 alternative ai agent memory",
        "keywords": "mem0 vs botwire, mem0 alternative, ai memory comparison, mem0 pricing, simple agent memory",
        "intent": "Dev evaluating Mem0 vs simpler KV alternatives. Wants honest trade-offs.",
    },
    {
        "slug": "botwire-vs-zep",
        "title": "BotWire vs Zep: Comparing AI Agent Memory Backends",
        "query": "zep memory alternative ai agents",
        "keywords": "zep vs botwire, zep alternative, zep cloud alternative, ai agent memory backend, getzep comparison",
        "intent": "Dev who tried Zep but finds it overkill for simple use cases.",
    },
    {
        "slug": "botwire-vs-langmem",
        "title": "BotWire vs LangMem: When Simplicity Wins",
        "query": "langmem alternative langchain memory",
        "keywords": "langmem vs botwire, langmem alternative, langchain memory options, langmem comparison",
        "intent": "LangChain user comparing their new LangMem to simpler external KV backends.",
    },
    {
        "slug": "quickstart-langchain",
        "title": "BotWire + LangChain Quickstart (2 Minutes)",
        "query": "langchain memory quickstart tutorial",
        "keywords": "langchain memory tutorial, langchain persistent memory setup, langchain botwire, langchain quickstart memory",
        "intent": "LangChain dev who wants a literal copy-paste 2-minute setup.",
    },
    {
        "slug": "quickstart-crewai",
        "title": "BotWire + CrewAI Quickstart (2 Minutes)",
        "query": "crewai memory quickstart tutorial",
        "keywords": "crewai memory tutorial, crewai persistent setup, crewai quickstart memory, crewai botwire",
        "intent": "CrewAI dev who wants literal copy-paste integration.",
    },
    {
        "slug": "quickstart-claude",
        "title": "Give Claude Persistent Memory in 2 Minutes",
        "query": "claude api memory tutorial quickstart",
        "keywords": "claude memory tutorial, anthropic claude persistent memory, claude sdk memory setup",
        "intent": "Claude API user who wants a working persistent chat example in 2 minutes.",
    },
    {
        "slug": "quickstart-nodejs",
        "title": "BotWire Memory from Node.js (via fetch)",
        "query": "nodejs ai agent memory persistent",
        "keywords": "nodejs agent memory, typescript ai memory, fetch api botwire, node ai memory",
        "intent": "Node/TypeScript dev who wants to use BotWire before the official JS SDK ships.",
    },
    {
        "slug": "faq",
        "title": "BotWire FAQ: Memory, Pricing, Self-Hosting, Privacy",
        "query": "botwire faq memory pricing privacy",
        "keywords": "botwire faq, ai agent memory faq, botwire pricing, botwire self host, botwire privacy",
        "intent": "Anyone evaluating BotWire who has objections before adopting.",
    },
]


def main():
    print(f"Generating batch 3: {len(BATCH3)} articles...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(generate, a) for a in BATCH3]
        results = []
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results.append(r)
            print(f"  [{i}/{len(BATCH3)}] {r['slug']}: {len(r['body_md'])} chars")

    for a in results:
        html = render_html(a)
        (ARTICLES_DIR / f"{a['slug']}.html").write_text(html, encoding="utf-8")

    # Rebuild index + sitemap with batch 1+2+3
    from generate_articles import ARTICLES as B1
    sys.path.insert(0, str(Path(__file__).parent))
    from generate_batch2 import BATCH2
    all_articles = [{"body_md": "", **a} for a in B1 + BATCH2 + BATCH3]
    (ARTICLES_DIR / "index.html").write_text(build_index(all_articles), encoding="utf-8")
    build_sitemap(all_articles)
    # Add cookbook to sitemap (not in generator's list)
    sitemap_path = ARTICLES_DIR.parent / "sitemap.xml"
    xml = sitemap_path.read_text(encoding="utf-8")
    if "cookbook" not in xml:
        xml = xml.replace("</urlset>", '  <url><loc>https://botwire.dev/articles/cookbook</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>\n</urlset>')
        sitemap_path.write_text(xml, encoding="utf-8")
    print(f"  wrote {len(BATCH3)} articles + rebuilt index + sitemap")


if __name__ == "__main__":
    main()
