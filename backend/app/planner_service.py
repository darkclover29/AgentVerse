"""Background planner: runs the slow LLM call OFF the tick loop.

The simulation thread submits a plan request (agent context + retrieved memories — both
gathered cheaply with SQL) and immediately moves on. A small thread pool performs the
Ollama call. Completed plans are drained by the sim thread via collect() and persisted
there, so ALL database writes stay single-threaded (no SQLite locking headaches).

Net effect: the clock never stalls waiting on the model. Agents act on an instant
heuristic plan and get upgraded to the LLM plan a moment later.
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from . import llm

log = logging.getLogger("agentverse.planner")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="planner")
_pending = {}          # agent_id -> Future[result dict]
_lock = threading.Lock()


def is_pending(agent_id: int) -> bool:
    with _lock:
        f = _pending.get(agent_id)
        return f is not None and not f.done()


def submit(agent_id: int, agent_ctx: dict, memories: list[str]) -> None:
    """Queue an LLM plan generation for this agent (no-op if one is already in flight)."""
    with _lock:
        existing = _pending.get(agent_id)
        if existing is not None and not existing.done():
            return
        _pending[agent_id] = _executor.submit(_run, agent_ctx, memories)


def _run(agent_ctx: dict, memories: list[str]) -> dict:
    try:
        return llm.generate_plan(agent_ctx, memories)
    except Exception as exc:  # never let a worker crash kill future planning
        log.warning("plan generation failed: %s", exc)
        return llm.fallback_plan(agent_ctx)


def collect() -> list[tuple[int, dict]]:
    """Return (agent_id, result) for every finished request and clear them."""
    out = []
    with _lock:
        for aid in [a for a, f in _pending.items() if f.done()]:
            f = _pending.pop(aid)
            try:
                out.append((aid, f.result()))
            except Exception as exc:
                log.warning("collect failed for agent %s: %s", aid, exc)
    return out
