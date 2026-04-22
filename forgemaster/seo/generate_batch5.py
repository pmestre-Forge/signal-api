"""Batch 5: frameworks, platforms, and agent ops."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import generate, render_html, ARTICLES_DIR, build_index, build_sitemap
from concurrent.futures import ThreadPoolExecutor, as_completed

BATCH5 = [
    {
        "slug": "mastra-ai-memory",
        "title": "Adding Persistent Memory to Mastra Agents",
        "query": "mastra ai agent memory persistent",
        "keywords": "mastra memory, mastra.ai agent, mastra persistent state, typescript ai agent memory",
        "intent": "Mastra (TypeScript agent framework) user whose agent loses context between runs.",
    },
    {
        "slug": "agno-agent-memory",
        "title": "Persistent Memory for Agno (formerly Phidata) Agents",
        "query": "agno phidata agent memory persistent",
        "keywords": "agno memory, phidata memory, agno persistent agent, phidata state",
        "intent": "Agno/Phidata user needing memory that survives across agent runs.",
    },
    {
        "slug": "inngest-ai-workflows-memory",
        "title": "Stateful AI Workflows with Inngest + BotWire",
        "query": "inngest ai workflow state persistent",
        "keywords": "inngest ai, inngest memory, durable workflow ai, inngest agent state",
        "intent": "Dev using Inngest for durable AI workflows that need long-term agent memory.",
    },
    {
        "slug": "temporal-ai-agents-memory",
        "title": "Long-Running AI Agents with Temporal + Memory",
        "query": "temporal ai agent memory workflow",
        "keywords": "temporal ai, temporal agent memory, durable ai workflow, temporal llm",
        "intent": "Backend engineer running Temporal workflows for AI agents that span hours or days.",
    },
    {
        "slug": "modal-ai-agent-memory",
        "title": "Modal.com AI Agents with Persistent Memory",
        "query": "modal ai agent memory serverless",
        "keywords": "modal.com ai agent, modal memory, modal serverless ai state, modal labs agent",
        "intent": "Modal user building agents on their serverless GPU platform who needs cross-run state.",
    },
    {
        "slug": "ai-agent-testing",
        "title": "Testing AI Agents: Memory Fixtures and Replay",
        "query": "how to test ai agent memory",
        "keywords": "ai agent testing, test ai memory, agent test fixtures, llm test harness, agent replay",
        "intent": "Engineer who wants deterministic tests for agents that depend on accumulated state.",
    },
    {
        "slug": "ai-agent-cost-optimization",
        "title": "Cutting AI Agent Costs with Persistent Memory",
        "query": "reduce llm agent cost memory caching",
        "keywords": "reduce llm cost, agent cost optimization, cache llm responses, token reduction memory",
        "intent": "Cost-conscious dev whose agent re-asks the same questions every run, burning tokens.",
    },
    {
        "slug": "ai-agent-evaluation",
        "title": "Evaluating AI Agents Over Time: Memory as Ground Truth",
        "query": "ai agent evaluation benchmark memory",
        "keywords": "agent evaluation, ai agent metrics, agent benchmarking, agent eval framework, langfuse alternative",
        "intent": "ML engineer trying to benchmark agent quality across versions using persisted state.",
    },
    {
        "slug": "multi-tenant-ai-agent",
        "title": "Multi-Tenant AI Agent Memory Patterns",
        "query": "multi-tenant ai agent memory isolation",
        "keywords": "multi-tenant ai, per-user agent memory, saas ai memory, tenant isolation agent, namespace pattern",
        "intent": "SaaS dev building per-customer agents who needs clean tenant isolation.",
    },
    {
        "slug": "ai-agent-scheduled-tasks",
        "title": "Scheduled AI Agent Tasks (Cron) with Persistent State",
        "query": "scheduled ai agent cron memory",
        "keywords": "cron ai agent, scheduled llm task, periodic ai agent, agent scheduler memory",
        "intent": "Dev running AI agents on cron that need to pick up where they left off last run.",
    },
]


def main():
    print(f"Generating batch 5: {len(BATCH5)} articles...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(generate, a) for a in BATCH5]
        results = []
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results.append(r)
            print(f"  [{i}/{len(BATCH5)}] {r['slug']}: {len(r['body_md'])} chars")

    for a in results:
        (ARTICLES_DIR / f"{a['slug']}.html").write_text(render_html(a), encoding="utf-8")

    # Rebuild with everything
    from generate_articles import ARTICLES as B1
    from generate_batch2 import BATCH2
    from generate_batch3 import BATCH3
    from generate_batch4 import BATCH4
    all_articles = [{"body_md": "", **a} for a in B1 + BATCH2 + BATCH3 + BATCH4 + BATCH5]
    all_articles.append({"slug": "cookbook", "title": "BotWire Memory Cookbook — 20 Recipes", "intent": "Copy-paste recipes for persistent memory patterns."})
    (ARTICLES_DIR / "index.html").write_text(build_index(all_articles), encoding="utf-8")
    build_sitemap(all_articles)
    print(f"  wrote {len(BATCH5)} articles + rebuilt index + sitemap")


if __name__ == "__main__":
    main()
