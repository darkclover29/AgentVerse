import pytest
import random
from app.models import Agent, Business, Event, Relationship, SimState
from app.events import append_event, KITTY_PARTY, MUTUAL_AID
from app.projections import reproject_all
from app.environment import is_flooded, is_traffic_gridlock, get_aqi
from app.movement import move_agents, _destination
from app.chat_service import _select_gossip

def test_environment_dynamics():
    # Test rain status on day 2 and day 3 (day % 5 in (2, 3))
    assert is_flooded(1, 5, day=2, tick=12) is True  # y in (5,6,7) and (x + y + day) % 4 == 0
    assert is_flooded(1, 5, day=1, tick=12) is False

    # Test traffic congestion row y=10 during rush hours (tick=8, 17)
    assert is_traffic_gridlock(5, 10, day=1, tick=8) is True
    assert is_traffic_gridlock(5, 10, day=1, tick=12) is False

    # Test AQI level fluctuations
    aqi_midday = get_aqi(day=1, tick=12)
    aqi_night = get_aqi(day=1, tick=2)
    assert aqi_midday > aqi_night


def test_kitty_party_event_execution(db):
    # Setup agents for kitty party
    s = db.get(SimState, 1) or SimState(day=0, tick=0, kitty_pool=100.0)
    db.add(s)
    db.commit()

    agent1 = db.query(Agent).filter(Agent.faction == "unaligned").first()
    agent2 = db.query(Agent).filter(Agent.faction == "unaligned").offset(1).first()
    
    initial_pool = s.kitty_pool or 100.0
    initial_wealth1 = agent1.wealth
    initial_wealth2 = agent2.wealth

    # Trigger kitty party event
    append_event(db, day=1, tick=18, type=KITTY_PARTY, agent_id=agent1.id, target_id=agent2.id,
                 payload={"participants": [agent1.id, agent2.id]})
    db.commit()

    db.refresh(agent1)
    db.refresh(agent2)
    db.refresh(s)

    # 15 rupees should be taken from each participant and added to kitty_pool
    assert agent1.wealth == initial_wealth1 - 15.0
    assert agent2.wealth == initial_wealth2 - 15.0
    assert s.kitty_pool == initial_pool + 30.0


def test_mutual_aid_payouts(db):
    # Set kitty pool to comfortable amount
    s = db.get(SimState, 1) or SimState(day=0, tick=0, kitty_pool=100.0)
    s.kitty_pool = 150.0
    db.add(s)
    db.commit()

    agent = db.query(Agent).filter(Agent.faction == "unaligned").first()
    agent.wealth = 20.0
    db.commit()

    # Trigger mutual aid event
    append_event(db, day=1, tick=20, type=MUTUAL_AID, agent_id=agent.id,
                 payload={"amount": 50.0})
    db.commit()

    db.refresh(agent)
    db.refresh(s)

    # Wealth should increase by 50 and pool decrease by 50
    assert agent.wealth == 70.0
    assert s.kitty_pool == 100.0


def test_gossip_selection():
    # Setup some dummy memories
    a_mems = [
        "Day 1: Rajesh became a mechanic.",
        "Day 2: RTO inspectors were checking auto permit renewals near Sector 5.",
    ]
    b_mems = [
        "Day 1: Priya did chat.",
    ]

    # Rajesh should be filtered out if we query for Rajesh and Priya
    gossip = _select_gossip(a_mems, b_mems, "Rajesh", "Priya")
    assert "Rajesh" not in gossip
    assert "Priya" not in gossip
    assert "RTO inspectors" in gossip
