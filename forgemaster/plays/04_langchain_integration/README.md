# BotWire Memory → LangChain / CrewAI Integration

## What this is
A single `memory.py` module that exposes:
1. `Memory(namespace)` — standalone HTTP client
2. `BotWireChatHistory(session_id)` — LangChain `BaseChatMessageHistory` adapter
3. `memory_tools(namespace)` — CrewAI tool bundle

## Next steps for real integration

### 1. Merge into the existing SDK
Move `memory.py` into `botwire-sdk/src/botwire/memory.py` and re-export from `__init__.py`:
```python
from botwire.memory import Memory, BotWireChatHistory, memory_tools
```

### 2. Optional deps in pyproject.toml
```toml
[project.optional-dependencies]
langchain = ["langchain-core>=0.1"]
crewai = ["crewai-tools>=0.1"]
all = ["langchain-core>=0.1", "crewai-tools>=0.1"]
```

### 3. Publish v0.2.0
```bash
cd botwire-sdk
rm -rf dist/
python -m build
twine upload dist/*
```

### 4. LangChain community PR (the big unlock)
After the SDK is stable, open a PR against `langchain-ai/langchain-community`:
- Path: `libs/community/langchain_community/chat_message_histories/botwire.py`
- Imports: `from botwire import Memory` (runtime only)
- Add test in their test suite
- PR title: "feat(chat_history): add BotWire persistent chat history"

**Why this matters:** once merged, anyone running `pip install langchain-community` gets the import path `from langchain_community.chat_message_histories import BotWireChatHistory`. That's organic discovery for every LangChain tutorial.

### 5. CrewAI tools registry
Similar PR to `crewAIInc/crewAI-tools` with the three tools above.

## Test script (run before publishing)
```python
from botwire import Memory

m = Memory("smoke-test")
m.set("k", "v")
assert m.get("k") == "v"
m.delete("k")
assert m.get("k") is None
print("OK")
```
