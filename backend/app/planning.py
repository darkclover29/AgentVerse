"""Tier-2 plan lifecycle: generate plans (LLM-grounded by memory) and execute them.

A Tier-2 agent holds one active Plan. Each "personal" phase tick it executes the next
step, which maps to a concrete event the engine already understands. When the steps run
out (or the plan ages), a new plan is generated.
"""
from __future__ import annotations

from . import economy, events as ev
from . import llm, memory, planner_service
from .models import Agent, Business, Plan, Relationship

PLAN_MAX_AGE_DAYS = 3


def _agent_ctx(agent: Agent) -> dict:
    return {
        "name": agent.name, "personality": agent.personality,
        "occupation": agent.occupation, "faction": agent.faction,
        "wealth": agent.wealth, "happiness": agent.happiness,
    }


def active_plan(db, agent_id: int) -> Plan | None:
    return (
        db.query(Plan)
        .filter(Plan.agent_id == agent_id, Plan.status == "active")
        .order_by(Plan.id.desc())
        .first()
    )


def _store_plan(db, agent: Agent, day: int, result: dict) -> Plan:
    """Persist a plan result as the agent's new active plan (retiring any prior one)."""
    prior = active_plan(db, agent.id)
    if prior:
        prior.status = "done"
    plan = Plan(
        agent_id=agent.id, day_created=day, goal=result["goal"],
        steps=result["steps"], step_index=0, status="active",
        source=result.get("source", "llm"),
    )
    db.add(plan)
    db.flush()
    ev.append_event(
        db, day=day, tick=0, type="plan", agent_id=agent.id,
        payload={"goal": result["goal"], "source": plan.source}, importance=0.8,
    )
    return plan


def persist_ready_plans(db, day: int) -> int:
    """Drain background-generated plans and persist them (called from the tick loop).
    All DB writes happen here, in the sim thread. Returns how many were applied."""
    applied = 0
    for agent_id, result in planner_service.collect():
        agent = db.get(Agent, agent_id)
        if agent and result:
            _store_plan(db, agent, day, result)
            applied += 1
    return applied


def ensure_plan(db, agent: Agent, day: int, rng) -> Plan:
    """Return a usable plan WITHOUT blocking on the LLM.

    - Active & fresh plan → use it.
    - Stale plan → keep using it, but request an LLM refresh in the background.
    - No plan → create an instant heuristic plan now and request the LLM one in the
      background (it replaces the heuristic plan when ready, via persist_ready_plans).
    """
    plan = active_plan(db, agent.id)
    stale = plan and (day - plan.day_created > PLAN_MAX_AGE_DAYS)

    if plan and not stale:
        return plan

    # kick off a background LLM plan (memory lookup is cheap SQL, done here)
    ctx = _agent_ctx(agent)
    memories = memory.recall(db, agent.id, ctx["faction"] + " goals rivals allies", k=5)
    planner_service.submit(agent.id, ctx, memories)

    if plan:                      # stale: keep current until the refresh lands
        return plan
    return _store_plan(db, agent, day, llm.fallback_plan(ctx, rng))  # instant


def _pick_rival(db, agent_id: int) -> int | None:
    r = (db.query(Relationship)
           .filter(Relationship.a_id == agent_id, Relationship.rivalry > 0)
           .order_by(Relationship.rivalry.desc()).first())
    return r.b_id if r else None


def _pick_ally(db, agent: Agent, rng) -> int | None:
    r = (db.query(Relationship)
           .filter(Relationship.a_id == agent.id, Relationship.friendship > 0)
           .order_by(Relationship.friendship.desc()).first())
    if r:
        return r.b_id
    other = (db.query(Agent)
               .filter(Agent.faction == agent.faction, Agent.id != agent.id).first())
    return other.id if other else None


def execute_step(db, agent: Agent, day: int, tick: int, rng):
    """Run the next step of the agent's active plan as an event. Returns the event type."""
    plan = ensure_plan(db, agent, day, rng)
    steps = plan.steps or []
    if plan.step_index >= len(steps):
        plan.status = "done"
        return None
    step = steps[plan.step_index]
    action = step.get("action")
    plan.step_index += 1
    if plan.step_index >= len(steps):
        plan.status = "done"

    if action == "found_business":
        owns = (db.query(Business)
                  .filter(Business.owner_id == agent.id, Business.status == "open")
                  .count())
        biz = None if owns >= 2 else economy.found_business(db, agent, day, tick, rng)
        if biz:
            economy.hire(db, biz, day, tick, rng)  # immediately staff it
            return "found_business"
        # not enough capital yet — fall back to earning
        ev.append_event(db, day=day, tick=tick, type=ev.EARN, agent_id=agent.id,
                        payload={"amount": 25.0}, importance=0.3)
        return "earn"
    if action == "work":
        ev.append_event(db, day=day, tick=tick, type=ev.WORK, agent_id=agent.id,
                        payload={"amount": 30.0, "happiness": 1}, importance=0.3)
        return "work"
    if action == "earn":
        ev.append_event(db, day=day, tick=tick, type=ev.EARN, agent_id=agent.id,
                        payload={"amount": 25.0}, importance=0.3)
        return "earn"
    if action == "seek_job":
        from .agents import OCCUPATIONS
        occ = rng.choice([o for o in OCCUPATIONS[agent.faction] if o != "unemployed"])
        ev.append_event(db, day=day, tick=tick, type=ev.JOB_CHANGE, agent_id=agent.id,
                        payload={"occupation": occ}, importance=0.5)
        return "seek_job"
    if action in ("network", "recruit_ally"):
        ally = _pick_ally(db, agent, rng)
        if ally:
            etype = ev.HELP if action == "recruit_ally" else ev.SOCIALIZE
            ev.append_event(db, day=day, tick=tick, type=etype, agent_id=agent.id,
                            target_id=ally, importance=0.6 if etype == ev.HELP else 0.3)
            return action
    if action == "undermine_rival":
        rival = _pick_rival(db, agent.id)
        if rival is None:
            other = (db.query(Agent)
                       .filter(Agent.id != agent.id).first())
            rival = other.id if other else None
        if rival:
            ev.append_event(db, day=day, tick=tick, type=ev.BETRAY, agent_id=agent.id,
                            target_id=rival, importance=0.8)
            return "undermine_rival"
            
    if action == "data_heist":
        # Hackers target a Corp business
        corp_bizs = (db.query(Business)
                       .filter(Business.status == "open", Business.btype.in_(["market_node", "fabrication_plant", "ad_agency"]))
                       .all())
        if corp_bizs:
            biz = rng.choice(corp_bizs)
            ev.append_event(db, day=day, tick=tick, type=ev.DATA_HEIST, agent_id=agent.id, target_id=biz.owner_id,
                            payload={"business_id": biz.id, "business_name": biz.name, "amount": 40.0}, importance=0.8)
            return "data_heist"
        # fallback
        ev.append_event(db, day=day, tick=tick, type=ev.EARN, agent_id=agent.id,
                        payload={"amount": 25.0}, importance=0.3)
        return "earn"

    if action == "shakedown":
        # Syndicate targets Unaligned business
        unaligned_bizs = (db.query(Business)
                            .filter(Business.status == "open", Business.btype.in_(["noodle_bar", "ripperdoc_clinic", "pawn_shop"]))
                            .all())
        if unaligned_bizs:
            biz = rng.choice(unaligned_bizs)
            ev.append_event(db, day=day, tick=tick, type=ev.SHAKEDOWN, agent_id=agent.id, target_id=biz.owner_id,
                            payload={"business_id": biz.id, "business_name": biz.name, "amount": 25.0}, importance=0.8)
            return "shakedown"
        # fallback
        ev.append_event(db, day=day, tick=tick, type=ev.EARN, agent_id=agent.id,
                        payload={"amount": 25.0}, importance=0.3)
        return "earn"

    if action == "lockdown":
        # Corp targets Syndicate/Hacker business
        target_bizs = (db.query(Business)
                         .filter(Business.status == "open", ~Business.btype.in_(["market_node", "fabrication_plant", "ad_agency", "noodle_bar", "ripperdoc_clinic", "pawn_shop"]))
                         .all())
        if target_bizs:
            biz = rng.choice(target_bizs)
            ev.append_event(db, day=day, tick=tick, type=ev.LOCKDOWN, agent_id=agent.id, target_id=biz.owner_id,
                            payload={"business_id": biz.id, "business_name": biz.name, "amount": 30.0}, importance=0.8)
            return "lockdown"
        # fallback
        ev.append_event(db, day=day, tick=tick, type=ev.EARN, agent_id=agent.id,
                        payload={"amount": 25.0}, importance=0.3)
        return "earn"

    if action == "mutual_aid":
        # Unaligned pools money to aid a failing Unaligned business
        failing = (db.query(Business)
                     .filter(Business.status == "open", Business.capital < 50.0, Business.btype.in_(["noodle_bar", "ripperdoc_clinic", "pawn_shop"]))
                     .all())
        if failing:
            biz = rng.choice(failing)
            ev.append_event(db, day=day, tick=tick, type=ev.MUTUAL_AID, agent_id=biz.owner_id,
                            payload={"business_id": biz.id, "business_name": biz.name, "amount": 30.0}, importance=0.7)
            return "mutual_aid"
        # fallback
        ev.append_event(db, day=day, tick=tick, type=ev.EARN, agent_id=agent.id,
                        payload={"amount": 25.0}, importance=0.3)
        return "earn"
    return None
