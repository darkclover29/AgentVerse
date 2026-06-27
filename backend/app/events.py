"""Event helpers: append events and apply their effect to projection tables.

Every state change flows through append_event(), which (1) writes the immutable event
and (2) folds it into the Agent / Relationship projections. To time-travel, you replay
events up to a target day against a fresh projection (see projections.replay_to_day).
"""
from .models import Agent, Event, Relationship, Business, SimState

# Event types
MOVE = "move"
WORK = "work"
EARN = "earn"
SOCIALIZE = "socialize"
HELP = "help"
BETRAY = "betray"
JOB_CHANGE = "job_change"
SLEEP = "sleep"
FOUND_BUSINESS = "found_business"
HIRE = "hire"
REVENUE = "revenue"
BANKRUPT = "bankrupt"
CONSUME = "consume"
CHAT = "chat"
DATA_HEIST = "data_heist"
SHAKEDOWN = "shakedown"
LOCKDOWN = "lockdown"
MUTUAL_AID = "mutual_aid"
KITTY_PARTY = "kitty_party"


def _rel(db, a_id, b_id):
    """Get or create the directed relationship a -> b."""
    rel = (
        db.query(Relationship)
        .filter(Relationship.a_id == a_id, Relationship.b_id == b_id)
        .first()
    )
    if rel is None:
        rel = Relationship(a_id=a_id, b_id=b_id, trust=0, friendship=0, rivalry=0)
        db.add(rel)
    return rel


def _clamp(v, lo=-100, hi=100):
    return max(lo, min(hi, v))


def apply_event(db, ev: Event):
    """Fold an event into the projections. Pure-ish: only touches Agent/Relationship/Business."""
    agent = db.get(Agent, ev.agent_id) if ev.agent_id else None
    p = ev.payload or {}

    if ev.type == MOVE and agent:
        agent.x, agent.y = p.get("x", agent.x), p.get("y", agent.y)
        agent.energy = _clamp(agent.energy - 1.0, 0, 100)

    elif ev.type == EARN and agent:
        agent.wealth += p.get("amount", 0)
        agent.energy = _clamp(agent.energy - 5.0, 0, 100)

    elif ev.type == WORK and agent:
        agent.wealth += p.get("amount", 0)
        agent.energy = _clamp(agent.energy - 8.0, 0, 100)
        agent.happiness = _clamp(agent.happiness + p.get("happiness", 0), 0, 100)

    elif ev.type == JOB_CHANGE and agent:
        agent.occupation = p.get("occupation", agent.occupation)

    elif ev.type == SLEEP and agent:
        agent.energy = 100.0

    elif ev.type == SOCIALIZE and agent and ev.target_id:
        agent.happiness = _clamp(agent.happiness + 3.0, 0, 100)
        for x, y in ((ev.agent_id, ev.target_id), (ev.target_id, ev.agent_id)):
            rel = _rel(db, x, y)
            rel.friendship = _clamp(rel.friendship + 5.0)
            rel.trust = _clamp(rel.trust + 2.0)

    elif ev.type == HELP and agent and ev.target_id:
        rel = _rel(db, ev.target_id, ev.agent_id)  # target now trusts actor
        rel.trust = _clamp(rel.trust + 10.0)
        rel.friendship = _clamp(rel.friendship + 5.0)

    elif ev.type == BETRAY and agent and ev.target_id:
        rel = _rel(db, ev.target_id, ev.agent_id)
        rel.trust = _clamp(rel.trust - 15.0)
        rel.rivalry = _clamp(rel.rivalry + 12.0)

    elif ev.type == FOUND_BUSINESS:
        if agent:
            agent.wealth -= 120.0  # FOUND_COST
        biz = Business(
            name=p.get("name"),
            btype=p.get("btype"),
            owner_id=ev.agent_id,
            x=agent.x if agent else p.get("x", 0),
            y=agent.y if agent else p.get("y", 0),
            capital=120.0,
            employees=[],
            day_founded=ev.day,
            status="open",
        )
        db.add(biz)

    elif ev.type == HIRE:
        biz = db.query(Business).filter(Business.owner_id == ev.agent_id, Business.name == p.get("business"), Business.status == "open").first()
        candidate = db.get(Agent, ev.target_id)
        if biz and candidate:
            biz.employees = list(biz.employees or []) + [candidate.id]
            candidate.occupation = f"{biz.btype} worker"

    elif ev.type == REVENUE:
        biz = db.query(Business).filter(Business.owner_id == ev.agent_id, Business.name == p.get("business"), Business.status == "open").first()
        if biz:
            net = p.get("net", 0.0)
            adjust = p.get("adjust", net)
            biz.capital += adjust
            if net > 0:
                owner = db.get(Agent, ev.agent_id)
                if owner:
                    owner.wealth += net * 0.5
                    biz.capital -= net * 0.5
            for emp_id in (biz.employees or []):
                emp = db.get(Agent, emp_id)
                if emp:
                    emp.wealth += 12.0  # WAGE is 12.0

    elif ev.type == BANKRUPT:
        biz = db.query(Business).filter(Business.owner_id == ev.agent_id, Business.name == p.get("business")).first()
        if biz:
            biz.status = "bankrupt"
            for emp_id in (biz.employees or []):
                emp = db.get(Agent, emp_id)
                if emp:
                    emp.occupation = "unemployed"
            biz.employees = []

    elif ev.type == CONSUME and agent:
        cost = p.get("amount", 15.0)
        agent.wealth -= cost
        biz_id = p.get("business_id")
        biz = db.get(Business, biz_id) if biz_id else None
        if biz:
            biz.capital += cost
        if p.get("need") == "energy":
            agent.energy = _clamp(agent.energy + 40.0, 0, 100)
        else:
            agent.happiness = _clamp(agent.happiness + 25.0, 0, 100)

    elif ev.type == DATA_HEIST:
        biz = db.get(Business, p.get("business_id"))
        if biz:
            biz.capital -= p.get("amount", 40.0)
        if agent:
            agent.wealth += p.get("amount", 40.0)

    elif ev.type == SHAKEDOWN:
        biz = db.get(Business, p.get("business_id"))
        if biz:
            biz.capital -= p.get("amount", 25.0)
        if agent:
            agent.wealth += p.get("amount", 25.0)

    elif ev.type == LOCKDOWN:
        biz = db.get(Business, p.get("business_id"))
        if biz:
            biz.capital -= p.get("amount", 30.0)

    elif ev.type == MUTUAL_AID:
        amount = p.get("amount", 50.0)
        state = db.get(SimState, 1)
        payout = amount
        if state:
            # Don't let kitty pool go negative
            if (state.kitty_pool or 0.0) < payout:
                payout = max(0.0, state.kitty_pool or 0.0)
            state.kitty_pool = max(0.0, (state.kitty_pool or 0.0) - payout)
            
        biz_id = p.get("business_id")
        if biz_id:
            biz = db.get(Business, biz_id)
            if biz:
                biz.capital += payout
        else:
            receiver = db.get(Agent, ev.agent_id)
            if receiver:
                receiver.wealth += payout

    elif ev.type == KITTY_PARTY:
        participants = p.get("participants", [])
        state = db.get(SimState, 1)
        contrib = 15.0
        total_contrib = 0.0
        for pid in participants:
            agent = db.get(Agent, pid)
            if agent:
                agent.wealth = max(0.0, agent.wealth - contrib)
                agent.happiness = _clamp(agent.happiness + 15.0, 0, 100)
                total_contrib += contrib
        if state:
            state.kitty_pool = (state.kitty_pool or 0.0) + total_contrib
            
        # Boost mutual trust/friendship between participants
        for i, id_a in enumerate(participants):
            for id_b in participants[i+1:]:
                for x, y in ((id_a, id_b), (id_b, id_a)):
                    rel = _rel(db, x, y)
                    rel.friendship = _clamp(rel.friendship + 4.0)
                    rel.trust = _clamp(rel.trust + 2.0)


def append_event(db, *, day, tick, type, agent_id=None, target_id=None,
                 payload=None, importance=0.1, _apply=True):
    ev = Event(
        day=day, tick=tick, type=type, agent_id=agent_id, target_id=target_id,
        payload=payload or {}, importance=importance,
    )
    db.add(ev)
    if _apply:
        apply_event(db, ev)
    return ev

