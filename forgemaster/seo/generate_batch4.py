"""Batch 4: 10 more long-tail — voice, RAG, observability, streaming, and more frameworks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from generate_articles import generate, render_html, ARTICLES_DIR, build_index, build_sitemap
from concurrent.futures import ThreadPoolExecutor, as_completed

BATCH4 = [
    {
        "slug": "haystack-agent-memory",
        "title": "Persistent Memory for Haystack Agents",
        "query": "haystack ai agent memory",
        "keywords": "haystack memory, deepset haystack agent state, haystack persistent, haystack context",
        "intent": "Haystack user running agent pipelines that lose state between runs.",
    },
    {
        "slug": "pydantic-ai-memory",
        "title": "Adding Persistent Memory to Pydantic AI Agents",
        "query": "pydantic ai memory persistent",
        "keywords": "pydantic ai memory, pydantic agents state, pydantic-ai memory, pydantic agent persistence",
        "intent": "Pydantic AI user who wants state between Agent.run() calls.",
    },
    {
        "slug": "vercel-ai-sdk-memory",
        "title": "Vercel AI SDK: Persistent Memory Across Sessions",
        "query": "vercel ai sdk memory persistent state",
        "keywords": "vercel ai sdk memory, ai sdk nextjs state, vercel ai persistent chat, edge functions memory",
        "intent": "Next.js dev using Vercel AI SDK whose chat state vanishes with every deployment.",
    },
    {
        "slug": "replit-agents-memory",
        "title": "Giving Replit Agents Persistent Memory",
        "query": "replit agent memory persistent",
        "keywords": "replit agent memory, replit ai persistent, replit agent state, replit bot memory",
        "intent": "Replit dev building agents that restart from scratch every time the Repl wakes up.",
    },
    {
        "slug": "voice-agent-memory",
        "title": "Persistent Memory for Voice AI Agents (ElevenLabs, Vapi, Retell)",
        "query": "voice ai agent memory persistent",
        "keywords": "voice agent memory, elevenlabs memory, vapi memory, retell ai memory, voice bot persistence",
        "intent": "Voice agent builder whose AI phone agent forgets every call.",
    },
    {
        "slug": "rag-plus-memory",
        "title": "RAG + Memory: When to Use Each (and Both)",
        "query": "rag vs memory ai agent",
        "keywords": "rag vs memory, agent rag memory, hybrid rag memory, retrieval vs state",
        "intent": "AI engineer confused about when a vector DB beats a KV store and when you need both.",
    },
    {
        "slug": "agent-observability-memory",
        "title": "Agent Observability: Audit Logs + Memory Snapshots",
        "query": "ai agent observability logs memory",
        "keywords": "agent observability, agent logs memory, ai agent debugging, agent tracing",
        "intent": "DevOps-minded dev wanting to understand what their agent did, why, and replay its state.",
    },
    {
        "slug": "streaming-chat-memory",
        "title": "Streaming LLM Chats With Persistent Memory",
        "query": "streaming llm chat persistent memory",
        "keywords": "streaming chat memory, llm streaming state, chat stream persistence, ai chat memory stream",
        "intent": "Dev building a streaming chat UI (SSE/WebSocket) who needs memory that survives the stream.",
    },
    {
        "slug": "slack-bot-ai-memory",
        "title": "Slack Bot With AI Memory (Per User, Per Channel)",
        "query": "slack ai bot persistent memory",
        "keywords": "slack bot memory, slack ai agent, slack bolt memory, slack chatbot state",
        "intent": "Slack bot dev whose AI answers forget channel context every deploy.",
    },
    {
        "slug": "whatsapp-ai-memory",
        "title": "WhatsApp AI Assistant With Persistent Memory",
        "query": "whatsapp ai assistant memory",
        "keywords": "whatsapp ai memory, whatsapp bot persistent, whatsapp chatbot state, twilio whatsapp ai",
        "intent": "Dev building a WhatsApp AI via Twilio/Meta whose chat history vanishes on restart.",
    },
]


def main():
    print(f"Generating batch 4: {len(BATCH4)} articles...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(generate, a) for a in BATCH4]
        results = []
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            results.append(r)
            print(f"  [{i}/{len(BATCH4)}] {r['slug']}: {len(r['body_md'])} chars")

    for a in results:
        html = render_html(a)
        (ARTICLES_DIR / f"{a['slug']}.html").write_text(html, encoding="utf-8")

    # Rebuild with all batches
    from generate_articles import ARTICLES as B1
    from generate_batch2 import BATCH2
    from generate_batch3 import BATCH3
    all_articles = [{"body_md": "", **a} for a in B1 + BATCH2 + BATCH3 + BATCH4]
    # Add cookbook and faq (already exist)
    (ARTICLES_DIR / "index.html").write_text(build_index(all_articles + [
        {"slug": "cookbook", "title": "BotWire Memory Cookbook — 20 Recipes", "intent": "Copy-paste recipes for persistent memory patterns."},
    ]), encoding="utf-8")
    build_sitemap(all_articles + [
        {"slug": "cookbook", "title": "Cookbook", "intent": ""},
    ])
    print(f"  wrote {len(BATCH4)} articles + rebuilt index + sitemap")


if __name__ == "__main__":
    main()
