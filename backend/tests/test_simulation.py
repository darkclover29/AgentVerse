"""Simulation engine: clock, movement, and non-blocking planning."""
import time

from app import planning, simulation
from app.models import Agent, Event, Plan


def test_step_advances_clock(db, grid):
    day, tick = simulation.step_n(db, grid, 25)  # just over a day
    assert (day, tick) == (1, 1)


def test_movement_emits_move_events(db, grid):
    simulation.step_n(db, grid, 24)
    assert db.query(Event).filter(Event.type == "move").count() > 0


def test_tier2_get_instant_plan_then_llm_upgrade(db, grid):
    # run a couple of days so Tier-2 agents pass through the planning (personal) phase
    simulation.step_n(db, grid, 24 * 2)
    t2 = db.query(Agent).filter(Agent.tier == 2).all()
    assert t2, "expected some Tier-2 agents"

    # at least some Tier-2 agents should have an active (fallback or LLM) plan
    planned = [a for a in t2 if planning.active_plan(db, a.id) is not None]
    assert planned, "at least one Tier-2 agent should have planned"

    # draining background-generated plans must not break the active-plan invariant
    time.sleep(1.0)
    planning.persist_ready_plans(db, day=3)
    db.flush()
    assert any(planning.active_plan(db, a.id) is not None for a in t2)
