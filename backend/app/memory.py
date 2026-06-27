"""Memory for Tier-2 agents.

Each important event becomes a textual memory. When a Tier-2 agent plans, it retrieves
the most relevant memories to ground the LLM prompt (RAG over the agent's own history).

Two backends, chosen automatically:
  - ChromaDB (semantic vector search) if `chromadb` is installed.
  - Fallback: relevance scoring over the Event table (importance + recency + keyword
    overlap). No extra dependency; the simulation runs the same either way.
"""
from __future__ import annotations
import os

from .models import Agent, Event

try:
    import chromadb
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    _CHROMA = chromadb.PersistentClient(path=db_path)
    _COLLECTION = _CHROMA.get_or_create_collection("agent_memories")
    HAVE_CHROMA = True
except Exception:  # chromadb not installed or failed to init
    _COLLECTION = None
    _CHROMA = None
    HAVE_CHROMA = False


def reset_chroma():
    """Clear ChromaDB collection for reprojection."""
    global _CHROMA, _COLLECTION
    if HAVE_CHROMA and _CHROMA:
        try:
            _CHROMA.delete_collection("agent_memories")
            _COLLECTION = _CHROMA.get_or_create_collection("agent_memories")
        except Exception:
            pass


def describe_event(db, ev: Event) -> str:
    """Turn an event into a first-person-ish memory line."""
    names = {a.id: a.name for a in db.query(Agent).all()}
    actor = names.get(ev.agent_id, f"Agent {ev.agent_id}")
    target = names.get(ev.target_id, "")
    p = ev.payload or {}
    if ev.type == "betray":
        return f"Day {ev.day}: {actor} betrayed {target}."
    if ev.type == "help":
        return f"Day {ev.day}: {actor} helped {target}."
    if ev.type == "job_change":
        return f"Day {ev.day}: {actor} became a {p.get('occupation', 'worker')}."
    if ev.type == "work":
        return f"Day {ev.day}: {actor} earned {p.get('amount', 0):.0f} from work."
    if ev.type == "chat":
        gossip = p.get("gossip_topic")
        if gossip:
            if gossip.startswith("Day "):
                parts = gossip.split(":", 1)
                if len(parts) > 1:
                    gossip = parts[1].strip()
            return f"Day {ev.day}: {actor} and {target} shared gossip: {gossip}"
        return f"Day {ev.day}: {actor} and {target} chatted."
    return f"Day {ev.day}: {actor} did {ev.type}."


def index_event(db, ev: Event):
    """Store a memory for the actor (and target, if any). Only called for Tier-2 agents."""
    if not HAVE_CHROMA:
        return  # fallback reads straight from the Event table, nothing to store
    text = describe_event(db, ev)
    ids, docs, metas = [], [], []
    for who in filter(None, (ev.agent_id, ev.target_id)):
        ids.append(f"{ev.id}:{who}")
        docs.append(text)
        metas.append({"agent_id": who, "day": ev.day, "importance": ev.importance})
    if ids:
        _COLLECTION.add(ids=ids, documents=docs, metadatas=metas)


def recall(db, agent_id: int, query: str, k: int = 5) -> list[str]:
    """Return up to k memory strings most relevant to `query` for this agent."""
    if HAVE_CHROMA:
        try:
            res = _COLLECTION.query(
                query_texts=[query], n_results=k,
                where={"agent_id": agent_id},
            )
            return res.get("documents", [[]])[0]
        except Exception:
            pass  # fall through to heuristic

    # Fallback: score this agent's events by importance + recency + keyword overlap.
    rows = (
        db.query(Event)
        .filter((Event.agent_id == agent_id) | (Event.target_id == agent_id))
        .order_by(Event.id.desc())
        .limit(300)
        .all()
    )
    if not rows:
        return []
    max_day = max(r.day for r in rows) or 1
    q_tokens = set(query.lower().split())
    scored = []
    for r in rows:
        text = describe_event(db, r)
        overlap = len(q_tokens & set(text.lower().split()))
        recency = r.day / max_day
        score = r.importance * 2 + recency + overlap * 0.5
        scored.append((score, text))
    scored.sort(reverse=True)
    seen, out = set(), []
    for _, text in scored:
        if text not in seen:
            seen.add(text)
            out.append(text)
        if len(out) >= k:
            break
    return out
