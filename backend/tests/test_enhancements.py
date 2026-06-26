import pytest
import random
from app.models import Agent, Business, Event, Relationship, Plan
from app.events import append_event, CONSUME, DATA_HEIST, SHAKEDOWN, LOCKDOWN, MUTUAL_AID
from app.projections import reproject_all
from app.planning import execute_step


def test_closed_loop_consumption(db):
    # Setup agent and business
    agent = db.query(Agent).filter(Agent.wealth >= 50).first()
    initial_wealth = agent.wealth
    
    biz = Business(
        name="Test ripperdoc",
        btype="ripperdoc_clinic",
        owner_id=2,
        x=5, y=5,
        capital=100.0,
        status="open"
    )
    db.add(biz)
    db.commit()
    
    # Trigger consume
    append_event(db, day=1, tick=5, type=CONSUME, agent_id=agent.id,
                 payload={"business_id": biz.id, "amount": 15.0, "need": "energy"})
    db.commit()
    
    # Reload stats
    db.refresh(agent)
    db.refresh(biz)
    
    assert agent.wealth == initial_wealth - 15.0
    assert biz.capital == 115.0
    assert agent.energy == 100.0  # clamped to 100


def test_reprojection_engine(db):
    # Append some events
    agent = db.query(Agent).first()
    append_event(db, day=1, tick=2, type="work", agent_id=agent.id, payload={"amount": 10.0})
    db.commit()
    
    # Get current state
    agents_before = {a.id: a.wealth for a in db.query(Agent).all()}
    
    # Run reprojection
    replayed = reproject_all(db)
    
    assert replayed >= 1
    agents_after = {a.id: a.wealth for a in db.query(Agent).all()}
    assert agents_before == agents_after


def test_faction_planning_actions(db):
    # Setup plan for Hacker
    hacker = db.query(Agent).filter(Agent.faction == "hacker").first()
    corp_biz = Business(
        name="Test Corp Market",
        btype="market_node",
        owner_id=2,
        x=5, y=5,
        capital=100.0,
        status="open"
    )
    db.add(corp_biz)
    db.commit()
    
    # Set a plan step for data_heist
    plan = Plan(
        agent_id=hacker.id,
        day_created=0,
        goal="Hack some corp data",
        steps=[{"action": "data_heist", "note": "steal wealth"}],
        step_index=0,
        status="active"
    )
    db.add(plan)
    db.commit()
    
    rng = random.Random(42)
    action = execute_step(db, hacker, day=0, tick=1, rng=rng)
    db.commit()
    
    assert action == "data_heist"
    db.refresh(corp_biz)
    db.refresh(hacker)
    
    # check that capital was stolen
    assert corp_biz.capital == 60.0  # 100 - 40
