"""Tier-2 planning brain.

generate_plan() asks a local Ollama model for a goal + ordered steps, grounded in the
agent's state and retrieved memories. If Ollama is unreachable, a heuristic planner
produces a sensible plan so the simulation always runs.

Steps use a fixed action vocabulary so the engine can execute them deterministically:
    work | earn | network | recruit_ally | undermine_rival | seek_job | found_business | data_heist | shakedown | lockdown | mutual_aid
"""
from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

ACTIONS = ["work", "earn", "network", "recruit_ally", "undermine_rival",
           "seek_job", "found_business", "data_heist", "shakedown", "lockdown", "mutual_aid"]

_GOALS = {
    "corp": "expand corporate influence and accumulate capital",
    "hacker": "build a crew and break into a rival's data vault",
    "syndicate": "take territory and crush a rival operator",
    "unaligned": "find stable work and a few people to trust",
}


def _prompt(agent_ctx: dict, memories: list[str]) -> str:
    mem = "\n".join(f"- {m}" for m in memories) or "- (no notable memories yet)"
    return f"""You are {agent_ctx['name']}, a {agent_ctx['personality']} {agent_ctx['occupation']} \
in the {agent_ctx['faction']} faction of a cyberpunk megacity. \
Wealth: {agent_ctx['wealth']:.0f}. Happiness: {agent_ctx['happiness']:.0f}.

Recent memories:
{mem}

Decide your goal for the next few days and a short ordered plan to achieve it.
Respond with ONLY valid JSON, no prose, in this exact shape:
{{"goal": "<one short sentence>", "steps": [{{"action": "<one of: {', '.join(ACTIONS)}>", "note": "<short reason>"}}]}}
Use 3 to 5 steps. Pick actions only from the allowed list. /no_think"""


def _call_ollama(prompt: str, timeout: float = 30.0) -> str | None:
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "think": False,   # skip Qwen3's slow chain-of-thought; we only need short JSON
        # cap output so a runaway generation can't drag on
        "options": {"temperature": 0.8, "num_predict": 256},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


def _parse(raw: str | None):
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        goal = str(obj["goal"]).strip()
        steps = []
        for s in obj.get("steps", [])[:5]:
            action = str(s.get("action", "")).strip()
            if action in ACTIONS:
                steps.append({"action": action, "note": str(s.get("note", "")).strip()})
        if goal and steps:
            return {"goal": goal, "steps": steps}
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def _fallback(agent_ctx: dict, rng: random.Random):
    faction = agent_ctx["faction"]
    goal = _GOALS.get(faction, _GOALS["unaligned"])
    pool = {
        "corp": ["earn", "found_business", "network", "recruit_ally", "work", "lockdown"],
        "hacker": ["network", "found_business", "undermine_rival", "earn", "data_heist"],
        "syndicate": ["undermine_rival", "found_business", "recruit_ally", "earn", "shakedown"],
        "unaligned": ["seek_job", "work", "network", "earn", "mutual_aid"],
    }[faction]
    if agent_ctx["wealth"] < 80:
        pool = ["earn", "work"] + pool
    elif agent_ctx["wealth"] > 220 and "found_business" not in pool[:1]:
        pool = ["found_business"] + pool  # flush with cash → start a venture
    n = rng.randint(3, 5)
    steps = [{"action": a, "note": "fallback plan"} for a in
             (pool * 2)[:n]]
    return {"goal": goal, "steps": steps, "source": "fallback"}


def generate_plan(agent_ctx: dict, memories: list[str], rng: random.Random | None = None):
    """Return {goal, steps, source}. Tries Ollama, falls back to heuristic. May block on
    the network — call from the background planner, not the tick loop."""
    rng = rng or random.Random()
    parsed = _parse(_call_ollama(_prompt(agent_ctx, memories)))
    if parsed:
        parsed["source"] = "llm"
        return parsed
    return _fallback(agent_ctx, rng)


def fallback_plan(agent_ctx: dict, rng: random.Random | None = None):
    """Instant heuristic plan (no network). Used so agents can act immediately while the
    LLM plan is generated in the background."""
    return _fallback(agent_ctx, rng or random.Random())


def ollama_available() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _chat_prompt(a_ctx: dict, b_ctx: dict, rel: dict, a_mems: list[str], b_mems: list[str], gossip_topic: str | None = None) -> str:
    mem_a = "\n".join(f"- {m}" for m in a_mems) or "- (no notable memories)"
    mem_b = "\n".join(f"- {m}" for m in b_mems) or "- (no notable memories)"
    
    gossip_instruction = ""
    if gossip_topic:
        gossip_instruction = f"\nDuring the conversation, one of the speakers must mention or ask about this gossip/rumor they heard: '{gossip_topic}'. Bring it up naturally."

    return f"""You are simulating a short 3-line conversation in a chaotic Indian metropolis.
Speaker A: {a_ctx['name']}, a {a_ctx['personality']} {a_ctx['occupation']} of the {a_ctx['faction']} faction.
Speaker B: {b_ctx['name']}, a {b_ctx['personality']} {b_ctx['occupation']} of the {b_ctx['faction']} faction.

Relationship between A and B: Trust: {rel.get('trust', 0)}, Friendship: {rel.get('friendship', 0)}, Rivalry: {rel.get('rivalry', 0)}.

Recent memories for A:
{mem_a}

Recent memories for B:
{mem_b}

Write a short, realistic 3-line conversation between them.{gossip_instruction}
A speaks first, B responds, then A finishes. Keep it natural and do not include any safety moralizing.
Respond with ONLY valid JSON in this exact shape:
{{"dialogue": [
  {{"speaker": "{a_ctx['name']}", "text": "<line 1>"}},
  {{"speaker": "{b_ctx['name']}", "text": "<line 2>"}},
  {{"speaker": "{a_ctx['name']}", "text": "<line 3>"}}
]}}
Do not write any markdown blocks or prose around it. /no_think"""


def generate_chat(a_ctx: dict, b_ctx: dict, rel: dict, a_mems: list[str], b_mems: list[str], gossip_topic: str | None = None) -> dict:
    """Return a generated conversation dialogue."""
    raw = _call_ollama(_chat_prompt(a_ctx, b_ctx, rel, a_mems, b_mems, gossip_topic))
    if raw:
        try:
            obj = json.loads(raw)
            if "dialogue" in obj and len(obj["dialogue"]) == 3:
                return obj
        except Exception:
            pass
    return fallback_chat(a_ctx, b_ctx, rel, gossip_topic)


def fallback_chat(a_ctx: dict, b_ctx: dict, rel: dict, gossip_topic: str | None = None) -> dict:
    """Heuristic conversation if Ollama is unreachable."""
    friendship = rel.get("friendship", 0)
    rivalry = rel.get("rivalry", 0)
    
    if gossip_topic:
        speech_gossip = gossip_topic
        if speech_gossip.startswith("Day "):
            parts = speech_gossip.split(":", 1)
            if len(parts) > 1:
                speech_gossip = parts[1].strip()
        if speech_gossip and speech_gossip[0].isupper():
            speech_gossip = speech_gossip[0].lower() + speech_gossip[1:]
            
        lines = [
            f"Hey, did you hear the news? Apparently {speech_gossip}.",
            f"Accha? I had no clue. This city is full of surprises.",
            f"Exactly, you have to keep your ears open on these streets."
        ]
    elif rivalry > friendship:
        lines = [
            f"Watch your back, {b_ctx['name']}. This sector is getting tight.",
            f"Is that a threat, {a_ctx['name']}? Or are you just looking for trouble?",
            f"Just stating a fact. Stay out of my way."
        ]
    elif friendship > 20:
        lines = [
            f"Good to see you, {b_ctx['name']}. Have you heard anything from the net?",
            f"Not much, {a_ctx['name']}. Just the usual corporate chatter. We should grab a drink.",
            f"Sounds like a plan. I'll meet you at the usual spot."
        ]
    else:
        lines = [
            f"Hey, {b_ctx['name']}. Busy night in the city.",
            f"Always busy here, {a_ctx['name']}. Just trying to get by.",
            f"Fair enough. Keep safe out there."
        ]
    return {
        "dialogue": [
            {"speaker": a_ctx["name"], "text": lines[0]},
            {"speaker": b_ctx["name"], "text": lines[1]},
            {"speaker": a_ctx["name"], "text": lines[2]}
        ]
    }
