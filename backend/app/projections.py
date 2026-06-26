"""Read-model projections derived from the event stream.

- daily_news: template headlines from each day's high-importance events.
- relationship_graph: nodes + colored edges for the frontend graph.
- replay_to_day: rebuild agent/relationship projections from scratch up to a target day,
  which is exactly what powers the Time Machine.
"""
from collections import defaultdict

from . import events as ev
from .models import Agent, Business, Event, Relationship


def relationship_graph(db, min_strength: float = 10.0):
    agents = db.query(Agent).all()
    nodes = [{"id": a.id, "name": a.name, "faction": a.faction,
              "occupation": a.occupation} for a in agents]
    edges = []
    seen = set()
    for r in db.query(Relationship).all():
        key = tuple(sorted((r.a_id, r.b_id)))
        if key in seen:
            continue
        seen.add(key)
        if r.rivalry >= min_strength:
            edges.append({"source": r.a_id, "target": r.b_id,
                          "kind": "rivalry", "weight": r.rivalry})
        elif r.friendship >= min_strength:
            edges.append({"source": r.a_id, "target": r.b_id,
                          "kind": "friendship", "weight": r.friendship})
    return {"nodes": nodes, "edges": edges}


def daily_news(db, day: int, limit: int = 8):
    rows = (
        db.query(Event)
        .filter(Event.day == day, Event.importance >= 0.5)
        .order_by(Event.importance.desc())
        .limit(limit)
        .all()
    )
    names = {a.id: a.name for a in db.query(Agent).all()}
    headlines = []
    for e in rows:
        actor = names.get(e.agent_id, f"Agent {e.agent_id}")
        target = names.get(e.target_id, "")
        p = e.payload or {}
        if e.type == ev.FOUND_BUSINESS:
            headlines.append(f"{actor} opened {p.get('name', 'a new business')}.")
        elif e.type == ev.BANKRUPT:
            headlines.append(f"{p.get('business', 'A business')} went under — {actor} ruined.")
        elif e.type == ev.HIRE:
            headlines.append(f"{actor} hired {target} at {p.get('business', 'their venture')}.")
        elif e.type == ev.REVENUE and p.get("net", 0) < 0:
            headlines.append(f"{p.get('business', 'A business')} is bleeding money.")
        elif e.type == "plan":
            goal = p.get("goal", "a new scheme")
            headlines.append(f"{actor} set out to {goal}")
        elif e.type == ev.BETRAY:
            headlines.append(f"{actor} turned on {target} — trust shattered.")
        elif e.type == ev.HELP:
            headlines.append(f"{actor} backed {target} in a tight spot.")
        elif e.type == ev.JOB_CHANGE:
            occ = (e.payload or {}).get("occupation", "a new role")
            headlines.append(f"{actor} took up work as a {occ}.")
        else:
            headlines.append(f"{actor}: {e.type}")
    return {"day": day, "headlines": headlines}


def businesses(db):
    names = {a.id: a.name for a in db.query(Agent).all()}
    rows = db.query(Business).order_by(Business.id).all()
    return [{"id": b.id, "name": b.name, "btype": b.btype, "owner": names.get(b.owner_id, "?"),
             "owner_id": b.owner_id, "x": b.x, "y": b.y, "capital": round(b.capital, 1),
             "employees": len(b.employees or []), "status": b.status,
             "day_founded": b.day_founded} for b in rows]


def agent_history(db, agent_id: int):
    """Reconstruct an agent's wealth/happiness day by day from the event stream."""
    events = (db.query(Event)
                .filter((Event.agent_id == agent_id) | (Event.target_id == agent_id))
                .order_by(Event.day, Event.tick, Event.id).all())
    wealth, happiness = 0.0, 50.0
    by_day = {}
    for e in events:
        p = e.payload or {}
        if e.agent_id == agent_id:
            if e.type in (ev.WORK, ev.EARN):
                wealth += p.get("amount", 0)
            elif e.type == ev.FOUND_BUSINESS:
                wealth -= 120
            if e.type == ev.WORK:
                happiness = min(100, happiness + p.get("happiness", 0))
            elif e.type == ev.SOCIALIZE:
                happiness = min(100, happiness + 3)
        by_day[e.day] = {"day": e.day, "wealth": round(wealth, 1),
                         "happiness": round(happiness, 1)}
    return {"agent_id": agent_id, "series": list(by_day.values())}


def replay_to_day(db, target_day: int):
    """Reconstruct projection state up to (and including) target_day from events alone.

    Returns an in-memory snapshot without mutating the live projection tables — useful
    for the timeline scrubber. Demonstrates that state is a pure fold over events.
    """
    agents = {a.id: {"id": a.id, "name": a.name, "x": a.x, "y": a.y,
                     "wealth": 0.0, "happiness": 50.0, "energy": 100.0,
                     "occupation": a.occupation, "faction": a.faction,
                     "gender": a.gender, "background": a.background}
              for a in db.query(Agent).all()}
    rels = defaultdict(lambda: {"trust": 0.0, "friendship": 0.0, "rivalry": 0.0})

    q = (db.query(Event)
           .filter(Event.day <= target_day)
           .order_by(Event.day, Event.tick, Event.id))
    for e in q:
        a = agents.get(e.agent_id)
        p = e.payload or {}
        if a is None:
            continue
        if e.type == ev.MOVE:
            a["x"], a["y"] = p.get("x", a["x"]), p.get("y", a["y"])
        elif e.type in (ev.WORK, ev.EARN):
            a["wealth"] += p.get("amount", 0)
        elif e.type == ev.JOB_CHANGE:
            a["occupation"] = p.get("occupation", a["occupation"])
        elif e.type == ev.SOCIALIZE and e.target_id:
            rels[(e.agent_id, e.target_id)]["friendship"] += 5
        elif e.type == ev.BETRAY and e.target_id:
            rels[(e.target_id, e.agent_id)]["rivalry"] += 12
        elif e.type == ev.HELP and e.target_id:
            rels[(e.target_id, e.agent_id)]["trust"] += 10
    return {"day": target_day, "agents": list(agents.values())}


def reproject_all(db):
    """Truncate all projection tables (Agent, Relationship, Business, Plan)
    and rebuild them by replaying the Event log. Resets Chroma vector memory as well.
    """
    from .seed import get_grid, _prime_rivalries
    from .agents import generate_agents
    from .config import RANDOM_SEED
    from .events import apply_event
    from .models import Agent, Relationship, Business, Plan, Event
    from .memory import reset_chroma, index_event

    # 1. Fetch all events in order
    events = db.query(Event).order_by(Event.day, Event.tick, Event.id).all()

    # 2. Truncate projections
    db.query(Relationship).delete()
    db.query(Plan).delete()
    db.query(Business).delete()
    db.query(Agent).delete()
    db.commit()

    # 3. Re-seed initial agents and relationships
    grid = get_grid()
    for a in generate_agents(grid, seed=RANDOM_SEED):
        db.add(a)
    db.commit()
    _prime_rivalries(db)

    # 4. Reset Chroma memory collection
    reset_chroma()

    # 5. Replay events
    tier2_ids = {a.id for a in db.query(Agent).filter(Agent.tier == 2).all()}
    for ev_obj in events:
        apply_event(db, ev_obj)
        # Re-index Tier-2 memory
        if ev_obj.importance >= 0.5 and (ev_obj.agent_id in tier2_ids or ev_obj.target_id in tier2_ids):
            index_event(db, ev_obj)
            
    db.commit()
    return len(events)


def agent_timeline(db, agent_id: int, limit: int = 50) -> list[dict]:
    """Compile a chronological list of formatted key life events involving this agent."""
    from .models import Event, Agent
    from . import events as ev

    events = (
        db.query(Event)
        .filter((Event.agent_id == agent_id) | (Event.target_id == agent_id))
        .filter(Event.type != "move")
        .order_by(Event.day.desc(), Event.tick.desc(), Event.id.desc())
        .limit(limit)
        .all()
    )

    names = {a.id: a.name for a in db.query(Agent).all()}
    timeline = []

    for e in events:
        actor = names.get(e.agent_id, f"Agent {e.agent_id}")
        target = names.get(e.target_id, "")
        p = e.payload or {}
        text = ""
        is_actor = e.agent_id == agent_id

        if e.type == ev.FOUND_BUSINESS:
            text = f"Founded venture '{p.get('name')}'" if is_actor else f"Venture '{p.get('name')}' founded by {actor}"
        elif e.type == ev.HIRE:
            text = f"Hired {target} at '{p.get('business')}'" if is_actor else f"Hired by {actor} at '{p.get('business')}'"
        elif e.type == ev.BANKRUPT:
            text = f"Went bankrupt! Venture '{p.get('business')}' liquidated." if is_actor else f"Venture '{p.get('business')}' owned by {actor} liquidated."
        elif e.type == ev.CONSUME:
            text = f"Spent ₹{p.get('amount')} at '{p.get('business')}' for {p.get('need')} recovery"
        elif e.type == ev.BETRAY:
            text = f"⚠️ Betrayed {target}!" if is_actor else f"⚡ Betrayed by {actor}!"
        elif e.type == ev.HELP:
            text = f"🤝 Helped {target}" if is_actor else f"🤝 Supported by {actor}"
        elif e.type == "data_heist":
            text = f"💾 Siphoned ₹{p.get('amount')} from {p.get('business_name')}" if is_actor else f"🚨 Security breached! {actor} siphoned ₹{p.get('amount')} from your firm '{p.get('business_name')}'"
        elif e.type == "shakedown":
            text = f"💸 Extorted ₹{p.get('amount')} from {p.get('business_name')}" if is_actor else f"💸 Protection payment: Paid ₹{p.get('amount')} to {actor} for '{p.get('business_name')}'"
        elif e.type == "lockdown":
            text = f"🚨 Fined {p.get('business_name')} ₹{p.get('amount')} during encroachment drive" if is_actor else f"🚨 Fined ₹{p.get('amount')} by Authority {actor} during encroachment drive of '{p.get('business_name')}'"
        elif e.type == "mutual_aid":
            text = f"✊ Contributed ₹{p.get('amount')} to Mohalla fund for {p.get('business_name')}" if is_actor else f"✊ Received ₹{p.get('amount')} in Mohalla committee aid for '{p.get('business_name')}'"
        elif e.type == ev.JOB_CHANGE:
            text = f"Changed occupation to {p.get('occupation')}"
        elif e.type == "chat":
            lines = p.get("dialogue", [])
            first = lines[0]["text"] if lines else "..."
            text = f"💬 Spoke with {target}: \"{first[:40]}...\"" if is_actor else f"💬 Spoke with {actor}: \"{first[:40]}...\""
        elif e.type == ev.WORK:
            text = f"Worked shift, earned ₹{p.get('amount')}"
        elif e.type == ev.EARN:
            text = f"Earned side return ₹{p.get('amount')}"
        else:
            continue

        timeline.append({
            "id": e.id,
            "day": e.day,
            "tick": e.tick,
            "time": f"{e.tick:02d}:00",
            "type": e.type,
            "text": text,
            "importance": e.importance
        })

    return timeline
