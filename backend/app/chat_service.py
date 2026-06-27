"""Background chat generator: runs slow LLM calls off the main tick loop."""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from . import llm, memory, events as ev
from .models import Agent, Relationship, SimState

log = logging.getLogger("agentverse.chat")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chat")
_pending = {}          # tuple(a_id, b_id) -> Future[dialogue dict]
_lock = threading.Lock()


def submit(db: Session, agent_a: Agent, agent_b: Agent) -> None:
    """Queue a chat dialogue generation for the two agents if none is pending."""
    # Order IDs so keys are consistent
    a_id, b_id = min(agent_a.id, agent_b.id), max(agent_a.id, agent_b.id)
    key = (a_id, b_id)
    
    with _lock:
        existing = _pending.get(key)
        if existing is not None and not existing.done():
            return

    # cheap SQL lookups here in main thread
    a_ctx = {
        "name": agent_a.name, "personality": agent_a.personality,
        "occupation": agent_a.occupation, "faction": agent_a.faction,
        "wealth": agent_a.wealth, "happiness": agent_a.happiness,
    }
    b_ctx = {
        "name": agent_b.name, "personality": agent_b.personality,
        "occupation": agent_b.occupation, "faction": agent_b.faction,
        "wealth": agent_b.wealth, "happiness": agent_b.happiness,
    }
    
    # get relationship info
    rel_ab = (db.query(Relationship)
                .filter(Relationship.a_id == agent_a.id, Relationship.b_id == agent_b.id)
                .first())
    rel_ctx = {
        "trust": rel_ab.trust if rel_ab else 0.0,
        "friendship": rel_ab.friendship if rel_ab else 0.0,
        "rivalry": rel_ab.rivalry if rel_ab else 0.0,
    }
    
    # retrieve memories
    a_mems = memory.recall(db, agent_a.id, f"{agent_b.name} relationships", k=4)
    b_mems = memory.recall(db, agent_b.id, f"{agent_a.name} relationships", k=4)
    
    # Retrieve general memories for gossip selection
    a_gen = memory.recall(db, agent_a.id, "gossip news rumors", k=8)
    b_gen = memory.recall(db, agent_b.id, "gossip news rumors", k=8)
    gossip_topic = _select_gossip(a_gen, b_gen, agent_a.name, agent_b.name)
    
    with _lock:
        _pending[key] = _executor.submit(_run, a_ctx, b_ctx, rel_ctx, a_mems, b_mems, gossip_topic)


def _select_gossip(a_mems: list[str], b_mems: list[str], name_a: str, name_b: str) -> str:
    import random
    all_mems = list(a_mems) + list(b_mems)
    random.shuffle(all_mems)
    first_a = name_a.split()[0].lower()
    first_b = name_b.split()[0].lower()
    for m in all_mems:
        m_low = m.lower()
        # Verify it's an event description (not about A or B)
        if ":" in m_low and first_a not in m_low and first_b not in m_low:
            return m
            
    # Localized fallback gossip topics
    generic_topics = [
        "Sharma Sweets & Chaat was overcrowded during the evening hours.",
        "Traffic at Silk Board junction reached record delays.",
        "Municipal Corporation planned a new encroachment drive near the metro.",
        "RTO inspectors were checking auto permit renewals near Sector 5.",
        "A moonlighting developer was caught coding their startup in office hours."
    ]
    return random.choice(generic_topics)


def _run(a_ctx: dict, b_ctx: dict, rel_ctx: dict, a_mems: list[str], b_mems: list[str], gossip_topic: str) -> dict:
    try:
        res = llm.generate_chat(a_ctx, b_ctx, rel_ctx, a_mems, b_mems, gossip_topic)
        if res:
            res["gossip_topic"] = gossip_topic
        return res
    except Exception as exc:
        log.warning("conversation generation failed: %s", exc)
        res = llm.fallback_chat(a_ctx, b_ctx, rel_ctx, gossip_topic)
        if res:
            res["gossip_topic"] = gossip_topic
        return res


def persist_ready_chats(db: Session) -> int:
    """Drain completed conversations and write them as Events in the DB."""
    state = db.get(SimState, 1)
    if not state:
        return 0
        
    applied = 0
    with _lock:
        ready_keys = [k for k, f in _pending.items() if f.done()]
        for key in ready_keys:
            f = _pending.pop(key)
            try:
                result = f.result()
                if result and "dialogue" in result:
                    ev.append_event(
                        db, day=state.day, tick=state.tick, type=ev.CHAT,
                        agent_id=key[0], target_id=key[1],
                        payload={
                            "dialogue": result["dialogue"],
                            "gossip_topic": result.get("gossip_topic")
                        },
                        importance=0.6
                    )
                    applied += 1
            except Exception as exc:
                log.warning("persist chat failed for %s: %s", key, exc)
    return applied
