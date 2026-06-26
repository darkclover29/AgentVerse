"""Event sourcing: appending an event must fold correctly into the projections."""
from app import events as ev
from app.models import Agent, Relationship


def test_earn_increases_wealth(db):
    a = db.query(Agent).first()
    before = a.wealth
    ev.append_event(db, day=0, tick=9, type=ev.EARN, agent_id=a.id, payload={"amount": 50})
    db.flush()
    assert a.wealth == before + 50


def test_socialize_builds_friendship_both_ways(db):
    a, b = db.query(Agent).limit(2).all()
    ev.append_event(db, day=0, tick=17, type=ev.SOCIALIZE, agent_id=a.id, target_id=b.id)
    db.flush()
    ab = db.query(Relationship).filter_by(a_id=a.id, b_id=b.id).first()
    ba = db.query(Relationship).filter_by(a_id=b.id, b_id=a.id).first()
    assert ab.friendship > 0 and ba.friendship > 0


def test_betray_creates_rivalry(db):
    a, b = db.query(Agent).limit(2).all()
    ev.append_event(db, day=0, tick=18, type=ev.BETRAY, agent_id=a.id, target_id=b.id)
    db.flush()
    rel = db.query(Relationship).filter_by(a_id=b.id, b_id=a.id).first()
    assert rel.rivalry > 0 and rel.trust < 0


def test_sleep_restores_energy(db):
    a = db.query(Agent).first()
    a.energy = 10
    ev.append_event(db, day=0, tick=2, type=ev.SLEEP, agent_id=a.id)
    db.flush()
    assert a.energy == 100
