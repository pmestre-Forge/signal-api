"""
Submit all sitemap URLs to IndexNow.
Pings once — Bing/Yandex will crawl within minutes.
"""
import json
import urllib.request
import urllib.error

KEY = "ebd6a484f9eb524633a11f8b3d6e4537"
HOST = "botwire.dev"

URLS = [
    "https://botwire.dev/",
    "https://botwire.dev/articles/",
    "https://botwire.dev/articles/langchain-persistent-memory",
    "https://botwire.dev/articles/crewai-agent-memory",
    "https://botwire.dev/articles/autogen-agent-memory",
    "https://botwire.dev/articles/claude-agent-memory",
    "https://botwire.dev/articles/mcp-memory-server",
    "https://botwire.dev/articles/llamaindex-agent-memory",
    "https://botwire.dev/articles/langgraph-persistent-state",
    "https://botwire.dev/articles/semantic-kernel-memory",
    "https://botwire.dev/articles/openai-assistants-api-memory",
    "https://botwire.dev/articles/why-ai-agents-forget",
    "https://botwire.dev/articles/python-ai-agent-key-value-store",
    "https://botwire.dev/articles/multi-agent-shared-memory",
    "https://botwire.dev/articles/ai-agent-memory-vs-redis",
    "https://botwire.dev/articles/agent-memory-vs-pinecone",
    "https://botwire.dev/articles/ai-agent-user-preferences",
    "https://botwire.dev/articles/agent-long-term-memory-pattern",
    "https://botwire.dev/articles/discord-bot-ai-memory",
    "https://botwire.dev/articles/telegram-bot-ai-memory",
    "https://botwire.dev/articles/serverless-ai-agent-state",
    "https://botwire.dev/articles/ai-agent-session-state-fastapi",
    "https://botwire.dev/articles/cookbook",
]

payload = {
    "host": HOST,
    "key": KEY,
    "keyLocation": f"https://{HOST}/{KEY}.txt",
    "urlList": URLS,
}

# Bing is the primary endpoint; it syndicates to Yandex, Seznam, and IndexNow partners
endpoints = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]

for url in endpoints:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"[{url}] HTTP {r.status} — submitted {len(URLS)} URLs")
    except urllib.error.HTTPError as e:
        # 200/202 are success; IndexNow returns 200 OK for valid submissions
        print(f"[{url}] HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"[{url}] ERROR: {e}")
