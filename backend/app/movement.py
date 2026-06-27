"""Agent movement. Each tick an agent steps one tile toward a phase-based destination,
emitting a MOVE event so the frontend can animate and the Time Machine can replay paths.
"""
import random

from . import events as ev
from .models import Business
from .world import tiles_of_type
from .environment import is_flooded, is_traffic_gridlock

# cache of destination tile lists per grid id (computed once)
_dest_cache = {}


def _targets(grid):
    key = id(grid)
    if key not in _dest_cache:
        _dest_cache[key] = {
            "work": tiles_of_type(grid, "corp_tower") + tiles_of_type(grid, "market_node"),
            "leisure": tiles_of_type(grid, "plaza"),
            "home": tiles_of_type(grid, "hab_block"),
        }
    return _dest_cache[key]


ENERGY_BIZ = {"net_cafe", "ripperdoc_clinic", "clinic", "data_den", "chop_shop", "crypto_exchange"}
HAPPINESS_BIZ = {"noodle_bar", "bar", "pawn_shop", "ad_agency", "fight_pit", "smuggling_ring"}


def _destination(db, agent, phase, grid, agents_by_pos, rng, day):
    """Pick a target tile for this agent based on the daily phase and current needs."""
    # Weekend Kitty Parties: unaligned agents route to Plazas during weekend social phase
    if phase == "social" and agent.faction == "unaligned" and (day % 7) in (5, 6):
        t = _targets(grid)
        plazas = t.get("leisure", [])
        if plazas:
            # Route to a plaza deterministically based on agent ID so they split/group reasonably
            plaza = plazas[agent.id % len(plazas)]
            return plaza[0], plaza[1]

    # Check consumer needs first if during personal/social phase and agent can afford it
    if phase in ("personal", "social") and agent.wealth >= 20.0:
        open_bizs = db.query(Business).filter(Business.status == "open").all()
        
        # 1. Energy recovery need
        if agent.energy < 30.0 and open_bizs:
            ebizs = [b for b in open_bizs if b.btype in ENERGY_BIZ]
            if ebizs:
                nearest = min(ebizs, key=lambda b: abs(b.x - agent.x) + abs(b.y - agent.y))
                return nearest.x, nearest.y
                
        # 2. Happiness need
        if agent.happiness < 40.0 and open_bizs:
            hbizs = [b for b in open_bizs if b.btype in HAPPINESS_BIZ]
            if hbizs:
                nearest = min(hbizs, key=lambda b: abs(b.x - agent.x) + abs(b.y - agent.y))
                return nearest.x, nearest.y

    t = _targets(grid)
    if phase == "work" and t["work"]:
        # deterministic-ish per agent so they commute to a stable workplace
        return t["work"][agent.id % len(t["work"])]
    if phase == "social":
        # head toward a random other agent's location
        others = [a for a in agents_by_pos if a.id != agent.id]
        if others:
            o = rng.choice(others)
            return (o.x, o.y)
    if phase == "personal" and t["leisure"]:
        return t["leisure"][agent.id % len(t["leisure"])]
    # sleep / fallback: go home
    if t["home"]:
        return t["home"][agent.id % len(t["home"])]
    return (agent.x, agent.y)


def _step_toward(x, y, tx, ty):
    nx = x + (1 if tx > x else -1 if tx < x else 0)
    ny = y + (1 if ty > y else -1 if ty < y else 0)
    return nx, ny


def move_agents(db, agents, phase, day, tick, grid, rng):
    """Advance every agent one tile toward its destination (skips sleepers mostly)."""
    for agent in agents:
        if phase == "sleep" and rng.random() < 0.8:
            continue  # mostly stay put while sleeping
        tx, ty = _destination(db, agent, phase, grid, agents, rng, day)
        if (agent.x, agent.y) == (tx, ty):
            continue
        nx, ny = _step_toward(agent.x, agent.y, tx, ty)
        
        # Environmental Waterlogging & Traffic Gridlock penalties
        if is_flooded(nx, ny, day, tick):
            if rng.random() < 0.5:
                # Stalled: keep current position
                nx, ny = agent.x, agent.y
            # Extra energy drain (Flooded costs total of 3.0 energy, apply_event does 1.0, we do 2.0)
            agent.energy = max(0.0, agent.energy - 2.0)
        elif is_traffic_gridlock(nx, ny, day, tick):
            if rng.random() < 0.6:
                # Stalled: keep current position
                nx, ny = agent.x, agent.y
            # Extra energy drain (Traffic costs total of 4.0 energy, apply_event does 1.0, we do 3.0)
            agent.energy = max(0.0, agent.energy - 3.0)
            
        ev.append_event(db, day=day, tick=tick, type=ev.MOVE, agent_id=agent.id,
                        payload={"x": nx, "y": ny}, importance=0.05)
