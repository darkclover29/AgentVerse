"""Economy: founding, hiring, revenue, and bankruptcy under saturation."""
import random

from app import economy
from app.models import Agent, Business


def test_found_business_costs_capital(db):
    a = db.query(Agent).first()
    a.wealth = 300
    rng = random.Random(1)
    biz = economy.found_business(db, a, day=0, tick=21, rng=rng)
    db.flush()
    assert biz is not None
    assert biz.owner_id == a.id
    assert a.wealth == 300 - economy.FOUND_COST


def test_cannot_found_when_broke(db):
    a = db.query(Agent).first()
    a.wealth = 50
    assert economy.found_business(db, a, 0, 21, random.Random(1)) is None


def test_hire_assigns_employee(db):
    owner = db.query(Agent).first()
    owner.wealth = 300
    rng = random.Random(2)
    biz = economy.found_business(db, owner, 0, 21, rng)
    db.flush()
    hired = economy.hire(db, biz, 0, 21, rng)
    db.flush()
    assert hired is not None
    assert hired.id in biz.employees


def test_saturated_market_goes_bankrupt(db):
    owners = db.query(Agent).limit(6).all()
    rng = random.Random(3)
    for o in owners:
        o.wealth = 300
        b = economy.found_business(db, o, 0, 21, rng)
        b.btype = "market_node"   # force them into the same market
        b.capital = 15            # thin margin
    db.flush()
    for d in range(6):
        economy.run_daily_economics(db, d, rng)
    db.flush()
    assert db.query(Business).filter(Business.status == "bankrupt").count() > 0
