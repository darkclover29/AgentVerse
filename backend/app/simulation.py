"""The simulation engine: the tick loop that drives the world forward."""
import random

from . import economy, events as ev
from . import memory, movement, planning
from .agents import decide_action
from .config import TICKS_PER_DAY
from .models import Agent, SimState
from .environment import get_aqi


def _phase(tick: int) -> str:
    """Map a tick (0-23) to a daily phase."""
    if tick < 8:
        return "sleep"
    if tick < 16:
        return "work"
    if tick < 20:
        return "social"
    return "personal"


def _nearest_other(agent, agents, rng):
    """Pick a plausible social target: another agent, biased toward same faction."""
    others = [a for a in agents if a.id != agent.id]
    if not others:
        return None
    same = [a for a in others if a.faction == agent.faction]
    pool = same if same and rng.random() < 0.6 else others
    return rng.choice(pool)


def step_tick(db, grid):
    """Advance the world by one tick. Appends events for every agent's action."""
    state = db.get(SimState, 1)
    rng = random.Random((state.day * TICKS_PER_DAY + state.tick) * 7919)
    agents = db.query(Agent).all()
    phase = _phase(state.tick)

    # apply any LLM plans that finished generating in the background (non-blocking)
    planning.persist_ready_plans(db, state.day)
    
    # apply any finished chats from background
    try:
        from . import chat_service
        chat_service.persist_ready_chats(db)
    except Exception:
        pass

    # AQI determines passive happiness decay rate
    aqi = get_aqi(state.day, state.tick)
    decay_happiness = 1.0 if aqi > 250 else 0.5

    # apply passive decay: happiness decays faster in high AQI
    for agent in agents:
        if phase != "sleep":
            agent.energy = max(0.0, agent.energy - 1.0)
            agent.happiness = max(0.0, agent.happiness - decay_happiness)

    # everyone takes a step toward where they're headed this phase
    movement.move_agents(db, agents, phase, state.day, state.tick, grid, rng)

    # Weekend Kitty Parties: trigger for groups of unaligned agents on Plaza tiles
    kitty_party_attendees = set()
    if phase == "social" and (state.day % 7) in (5, 6):
        from .world import tiles_of_type
        plazas = tiles_of_type(grid, "plaza")
        for px, py in plazas:
            plaza_agents = [a for a in agents if a.x == px and a.y == py and a.faction == "unaligned"]
            if len(plaza_agents) >= 2:
                p_ids = [a.id for a in plaza_agents]
                ev.append_event(
                    db, day=state.day, tick=state.tick, type=ev.KITTY_PARTY,
                    agent_id=p_ids[0], target_id=p_ids[1] if len(p_ids) > 1 else None,
                    payload={"participants": p_ids}, importance=0.6
                )
                for a in plaza_agents:
                    kitty_party_attendees.add(a.id)

    from .models import Business
    open_bizs = db.query(Business).filter(Business.status == "open").all()
    biz_by_pos = {(b.x, b.y): b for b in open_bizs}

    for agent in agents:
        if agent.id in kitty_party_attendees:
            continue
        # Check if agent is on a business tile that satisfies their need
        biz = biz_by_pos.get((agent.x, agent.y))
        if biz and phase in ("personal", "social") and agent.wealth >= 20.0:
            if agent.energy < 30.0 and biz.btype in movement.ENERGY_BIZ:
                ev.append_event(db, day=state.day, tick=state.tick, type=ev.CONSUME,
                                agent_id=agent.id, payload={"business_id": biz.id, "amount": 15.0, "need": "energy"},
                                importance=0.4)
                continue
            if agent.happiness < 40.0 and biz.btype in movement.HAPPINESS_BIZ:
                ev.append_event(db, day=state.day, tick=state.tick, type=ev.CONSUME,
                                agent_id=agent.id, payload={"business_id": biz.id, "amount": 15.0, "need": "happiness"},
                                importance=0.4)
                continue

        # Tier-2 agents pursue an LLM-generated plan during the personal phase.
        if agent.tier == 2 and phase == "personal" and agent.energy >= 20:
            etype = planning.execute_step(db, agent, state.day, state.tick, rng)
            continue

        action, kwargs = decide_action(agent, phase, grid, rng)
        target_id = None
        importance = 0.1

        if action == "socialize":
            other = _nearest_other(agent, agents, rng)
            if other is None:
                continue
            target_id = other.id
            
            # Check if they are in the same tile and at least one is Tier-2 for dynamic chat
            if agent.x == other.x and agent.y == other.y and (agent.tier == 2 or other.tier == 2):
                if rng.random() < 0.20:
                    try:
                        from . import chat_service
                        chat_service.submit(db, agent, other)
                    except Exception:
                        pass
            
            # ambitious/ruthless agents occasionally betray instead of bond
            if agent.personality in ("ruthless", "reckless") and rng.random() < 0.15:
                action, importance = ev.BETRAY, 0.7
            elif rng.random() < 0.1:
                action, importance = ev.HELP, 0.6

        elif action == "job_change":
            importance = 0.5

        ev.append_event(
            db, day=state.day, tick=state.tick, type=action,
            agent_id=agent.id, target_id=target_id, payload=kwargs,
            importance=importance,
        )

    # index this tick's important events for Tier-2 agents' memory (no-op without ChromaDB)
    db.flush()
    tier2 = {a.id for a in agents if a.tier == 2}
    if tier2:
        from .models import Event
        recent = (db.query(Event)
                    .filter(Event.day == state.day, Event.tick == state.tick,
                            Event.importance >= 0.5)
                    .all())
        for e in recent:
            if e.agent_id in tier2 or e.target_id in tier2:
                memory.index_event(db, e)

    # advance clock; at end of day run the economy
    state.tick += 1
    if state.tick >= TICKS_PER_DAY:
        economy.run_daily_economics(db, state.day, rng)
        state.tick = 0
        state.day += 1
    db.commit()
    return state.day, state.tick


def step_n(db, grid, n: int):
    last = None
    for _ in range(n):
        last = step_tick(db, grid)
    return last
