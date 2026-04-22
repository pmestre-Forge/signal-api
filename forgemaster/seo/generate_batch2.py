"""Batch 2: 10 more long-tail articles covering adjacent queries."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import generate, render_html, ARTICLES_DIR, build_index, build_sitemap
from concurrent.futures import ThreadPoolExecutor, as_completed

BATCH2 = [
    {
        "slug": "llamaindex-agent-memory",
        "title": "Persistent Memory for LlamaIndex Agents",
        "query": "llamaindex agent memory persistent storage",
        "keywords": "llamaindex memory, llama-index agent state, llamaindex chat store, llamaindex persistence",
        "intent": "LlamaIndex user whose QueryEngine/Agent loses context across calls. Wants drop-in persistence.",
    },
    {
        "slug": "openai-assistants-api-memory",
        "title": "Adding External Memory to the OpenAI Assistants API",
        "query": "openai assistants api persistent memory external state",
        "keywords": "openai assistants memory, assistants api state, openai thread persistence, custom memory openai",
        "intent": "OpenAI Assistants API user who wants memory outside the thread — cross-thread, cross-user, searchable.",
    },
    {
        "slug": "agent-memory-vs-pinecone",
        "title": "BotWire Memory vs Pinecone: When to Use Which",
        "query": "agent memory vs pinecone vector db",
        "keywords": "botwire vs pinecone, agent kv vs vector db, when to use pinecone, pinecone alternative",
        "intent": "Dev comparing options, confused about when vector DBs are overkill for simple state.",
    },
    {
        "slug": "langgraph-persistent-state",
        "title": "LangGraph Persistent State Across Runs",
        "query": "langgraph checkpointer persistent state",
        "keywords": "langgraph state, langgraph checkpointer, langgraph persistent workflow, langgraph resume",
        "intent": "LangGraph user whose stateful graph loses progress between process restarts.",
    },
    {
        "slug": "ai-agent-user-preferences",
        "title": "How to Store Per-User Preferences for AI Agents",
        "query": "ai agent remember user preferences",
        "keywords": "user preferences ai agent, personalization ai agents, user profile agent storage, per-user state",
        "intent": "Product builder who wants their agent to remember each user's preferences across sessions.",
    },
    {
        "slug": "agent-long-term-memory-pattern",
        "title": "Short-Term vs Long-Term Memory for AI Agents",
        "query": "ai agent long term memory pattern",
        "keywords": "long term memory agent, short term agent memory, agent memory architecture, memory layers ai",
        "intent": "Designer deciding memory architecture — what goes in-context, what goes in KV, what goes in vector DB.",
    },
    {
        "slug": "semantic-kernel-memory",
        "title": "Persistent Memory for Semantic Kernel Agents",
        "query": "semantic kernel persistent memory plugin",
        "keywords": "semantic kernel memory, sk persistent plugin, microsoft semantic kernel state",
        "intent": "Semantic Kernel user who needs memory that survives restarts across C#/Python kernels.",
    },
    {
        "slug": "discord-bot-ai-memory",
        "title": "Building a Discord Bot With AI Memory (Per User, Per Channel)",
        "query": "discord bot ai memory per user",
        "keywords": "discord bot memory, ai discord bot persistent, discord bot user state, discord ai memory",
        "intent": "Discord bot dev whose AI responses forget user context every restart.",
    },
    {
        "slug": "telegram-bot-ai-memory",
        "title": "Telegram AI Bot With Persistent Memory Across Sessions",
        "query": "telegram ai bot memory persistent",
        "keywords": "telegram bot ai memory, telegram persistent bot, ai telegram bot state",
        "intent": "Telegram bot dev whose AI agent forgets chat history when the server restarts.",
    },
    {
        "slug": "serverless-ai-agent-state",
        "title": "State for Serverless AI Agents (Lambda, Cloud Run, Vercel)",
        "query": "serverless ai agent state lambda vercel",
        "keywords": "serverless agent state, lambda ai memory, vercel ai agent storage, cloud run ai state",
        "intent": "Dev running agents on ephemeral serverless compute that resets every invocation.",
    },
]


def main():
    print(f"Generating batch 2: {len(BATCH2)} articles...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(generate, a) for a in BATCH2]
        results = []
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results.append(r)
            print(f"  [{i}/{len(BATCH2)}] {r['slug']}: {len(r['body_md'])} chars")

    for a in results:
        html = render_html(a)
        (ARTICLES_DIR / f"{a['slug']}.html").write_text(html, encoding="utf-8")
        print(f"  wrote {a['slug']}.html")

    # Rebuild index + sitemap with ALL articles (batch 1 + batch 2)
    from generate_articles import ARTICLES as BATCH1
    all_articles = BATCH1 + BATCH2
    # The generate_articles build_index/build_sitemap expect dicts with body_md — but for index/sitemap only slug+title+intent are used. Add empty body_md for batch 1.
    enriched = []
    for a in all_articles:
        if "body_md" not in a:
            a = {**a, "body_md": ""}
        enriched.append(a)
    (ARTICLES_DIR / "index.html").write_text(build_index(enriched), encoding="utf-8")
    build_sitemap(enriched)
    print("  rebuilt index.html + sitemap.xml")


if __name__ == "__main__":
    main()
