"""Batch 6: agent-ops ecosystem (Helicone, AgentOps, Portkey, Arize, Langfuse, Braintrust, Humanloop, etc)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import generate, render_html, ARTICLES_DIR, build_index, build_sitemap
from concurrent.futures import ThreadPoolExecutor, as_completed

BATCH6 = [
    {
        "slug": "langfuse-plus-botwire",
        "title": "Langfuse + BotWire: Observability Meets Persistent Memory",
        "query": "langfuse memory agent state",
        "keywords": "langfuse memory, langfuse agent state, langfuse botwire, agent trace state",
        "intent": "Langfuse user who wants persistent state alongside LLM traces.",
    },
    {
        "slug": "helicone-plus-memory",
        "title": "Helicone + Memory: Tracking LLM Costs per Agent Namespace",
        "query": "helicone agent state memory",
        "keywords": "helicone memory, per-agent cost tracking, helicone botwire, llm observability memory",
        "intent": "Helicone user wanting to group LLM call costs by persistent agent namespace.",
    },
    {
        "slug": "portkey-gateway-memory",
        "title": "Portkey Gateway + BotWire Memory: Gateway + State",
        "query": "portkey llm gateway memory state",
        "keywords": "portkey memory, portkey gateway botwire, llm gateway state, portkey alternative",
        "intent": "Dev using Portkey as LLM gateway who also needs cross-invocation memory.",
    },
    {
        "slug": "arize-phoenix-memory",
        "title": "Arize Phoenix + Agent Memory: Tracing Stateful Agents",
        "query": "arize phoenix agent memory tracing",
        "keywords": "arize phoenix memory, agent tracing state, phoenix llm eval memory",
        "intent": "Arize Phoenix user tracing agent behavior across sessions.",
    },
    {
        "slug": "braintrust-eval-memory",
        "title": "Braintrust Evals for Agents with Persistent State",
        "query": "braintrust agent eval memory",
        "keywords": "braintrust memory, agent eval state, braintrustdata agent, stateful eval",
        "intent": "Braintrust user evaluating agents whose output depends on accumulated memory.",
    },
    {
        "slug": "humanloop-agent-memory",
        "title": "Humanloop + Persistent Memory for Prompt Iteration",
        "query": "humanloop memory agent state",
        "keywords": "humanloop memory, humanloop agent, prompt iteration memory, humanloop botwire",
        "intent": "Humanloop user iterating prompts whose agents need persistent state.",
    },
    {
        "slug": "agentops-plus-memory",
        "title": "AgentOps + BotWire: Observability + Durable State",
        "query": "agentops memory state persistent",
        "keywords": "agentops memory, agentops botwire, agent monitoring state, agentops alternative",
        "intent": "AgentOps user who needs persistent state separate from session traces.",
    },
    {
        "slug": "browserbase-agent-memory",
        "title": "Browserbase Agents With Persistent Memory",
        "query": "browserbase agent memory state",
        "keywords": "browserbase memory, browserbase agent, browser agent state, stagehand memory",
        "intent": "Browserbase/Stagehand user whose browser-automation agents lose state between runs.",
    },
    {
        "slug": "e2b-code-agents-memory",
        "title": "E2B Code Interpreter Agents + Persistent Memory",
        "query": "e2b code agent memory persistent",
        "keywords": "e2b memory, e2b agent state, code interpreter memory, e2b sandbox",
        "intent": "E2B user building code-interpreter agents that reset between sandboxed runs.",
    },
    {
        "slug": "pydantic-graph-agents-memory",
        "title": "Pydantic Graph Agents + Persistent State",
        "query": "pydantic graph agent memory state",
        "keywords": "pydantic graph memory, pydantic-graph agent, graph agent state, pydantic ai graph",
        "intent": "Pydantic Graph user whose nodes need to share and persist state across executions.",
    },
]


def main():
    print(f"Generating batch 6: {len(BATCH6)} articles...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(generate, a) for a in BATCH6]
        results = []
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results.append(r)
            print(f"  [{i}/{len(BATCH6)}] {r['slug']}: {len(r['body_md'])} chars")

    for a in results:
        (ARTICLES_DIR / f"{a['slug']}.html").write_text(render_html(a), encoding="utf-8")

    from generate_articles import ARTICLES as B1
    from generate_batch2 import BATCH2
    from generate_batch3 import BATCH3
    from generate_batch4 import BATCH4
    from generate_batch5 import BATCH5
    all_articles = [{"body_md": "", **a} for a in B1 + BATCH2 + BATCH3 + BATCH4 + BATCH5 + BATCH6]
    all_articles.append({"slug": "cookbook", "title": "BotWire Memory Cookbook - 20 Recipes", "intent": "Copy-paste recipes for persistent memory patterns."})
    (ARTICLES_DIR / "index.html").write_text(build_index(all_articles), encoding="utf-8")
    build_sitemap(all_articles)
    # Re-append playground + status + cookbook back to sitemap
    sp = ARTICLES_DIR.parent / "sitemap.xml"
    xml = sp.read_text(encoding="utf-8")
    extras = []
    if "/playground" not in xml:
        extras.append('  <url><loc>https://botwire.dev/playground</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>')
    if "/status" not in xml:
        extras.append('  <url><loc>https://botwire.dev/status</loc><changefreq>daily</changefreq><priority>0.6</priority></url>')
    if extras:
        xml = xml.replace("</urlset>", "\n".join(extras) + "\n</urlset>")
        sp.write_text(xml, encoding="utf-8")
    print(f"  wrote {len(BATCH6)} articles + rebuilt index + sitemap")


if __name__ == "__main__":
    main()
