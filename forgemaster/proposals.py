"""
Proposal queue.

A proposal is a "thing I might ship" — a new product, feature, pricing change,
content experiment. Each proposal goes through the Audit Legion and then to
the CEO agent for APPROVE/REJECT/MODIFY.

Storage: dogfooded on BotWire's own Memory API. Namespace: "fm-proposals".
"""
from __future__ import annotations
import json
import secrets
import time
from dataclasses import dataclass, asdict, field
from typing import Literal, Optional

# Import BotWire Memory — dogfood!
try:
    from botwire import Memory
except ImportError:
    # Fallback to HTTP client if SDK missing
    import httpx
    class Memory:
        def __init__(self, ns: str):
            self.ns = ns
            self.url = "https://botwire.dev"
        def set(self, k: str, v):
            v = v if isinstance(v, str) else json.dumps(v)
            httpx.put(f"{self.url}/memory/{self.ns}/{k}", json={"value": v}, timeout=10)
        def get(self, k: str, default=None):
            r = httpx.get(f"{self.url}/memory/{self.ns}/{k}", timeout=10)
            if r.status_code == 404:
                return default
            v = r.json().get("value", default)
            if isinstance(v, str) and v and v[0] in "[{":
                try: return json.loads(v)
                except: return v
            return v
        def delete(self, k: str):
            httpx.delete(f"{self.url}/memory/{self.ns}/{k}", timeout=10)
        def keys(self):
            r = httpx.get(f"{self.url}/memory/{self.ns}", timeout=10)
            return r.json().get("keys", []) if r.status_code == 200 else []


Status = Literal["pending", "auditing", "approved", "rejected", "modify", "executed", "failed"]
ProposalType = Literal["feature", "product", "pricing", "content", "infra", "positioning", "partnership"]


@dataclass
class Proposal:
    id: str
    title: str
    description: str
    proposer: str            # "forgemaster", "pedro", "agent_xxx"
    type: ProposalType
    status: Status = "pending"
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))

    # Populated by audit
    legion_verdict: Optional[dict] = None     # {verdict: KILL/PIVOT/INVEST/HOLD, synthesis: "...", raw_count: 104}

    # Populated by CEO
    ceo_decision: Optional[dict] = None       # {decision: APPROVE/REJECT/MODIFY, reasoning: "...", confidence: 0-1}
    executor_notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Proposal":
        return cls(**d)


_mem = Memory("fm-proposals")


def new_id() -> str:
    return f"prop_{int(time.time())}_{secrets.token_hex(4)}"


def create(title: str, description: str, ptype: ProposalType, proposer: str = "pedro") -> Proposal:
    p = Proposal(id=new_id(), title=title, description=description, proposer=proposer, type=ptype)
    save(p)
    return p


def save(p: Proposal) -> None:
    p.updated_at = int(time.time())
    _mem.set(p.id, p.to_dict())


def load(pid: str) -> Optional[Proposal]:
    d = _mem.get(pid)
    if not d:
        return None
    return Proposal.from_dict(d)


def list_all() -> list[Proposal]:
    raw = _mem.keys()
    # The API may return either ["k1","k2"] or [{"key":"k1",...}, ...]
    ids: list[str] = []
    for k in raw:
        if isinstance(k, str):
            ids.append(k)
        elif isinstance(k, dict) and "key" in k:
            ids.append(k["key"])
    out: list[Proposal] = []
    for pid in ids:
        d = _mem.get(pid)
        if d:
            try:
                out.append(Proposal.from_dict(d))
            except Exception:
                pass
    return sorted(out, key=lambda p: -p.created_at)


def list_pending() -> list[Proposal]:
    return [p for p in list_all() if p.status in ("pending", "auditing")]


def set_status(pid: str, status: Status, **fields) -> Proposal:
    p = load(pid)
    if not p:
        raise ValueError(f"Proposal not found: {pid}")
    p.status = status
    for k, v in fields.items():
        if hasattr(p, k):
            setattr(p, k, v)
    save(p)
    return p
