"""Business lifecycle: founding, hiring, daily revenue, and bankruptcy.

Businesses are projections kept alongside the event stream. Each business event
(found_business, hire, revenue, bankrupt) is appended so the news feed and Time Machine
stay consistent. Daily economics run once per simulated day.
"""
import random

from . import events as ev
from .models import Agent, Business

FOUND_COST = 120.0          # capital an agent sinks into a new venture
MIN_WEALTH_TO_FOUND = 200.0  # must be comfortably funded
WAGE = 12.0                  # paid to each employee per day
RENT = 16.0                  # fixed daily overhead — saturated markets can't cover it
BTYPE_BY_FACTION = {
    "corp": ["market_node", "fabrication_plant", "ad_agency"],
    "hacker": ["data_den", "crypto_exchange", "net_cafe"],
    "syndicate": ["smuggling_ring", "fight_pit", "chop_shop"],
    "unaligned": ["noodle_bar", "ripperdoc_clinic", "pawn_shop"],
}
_NAME_BITS = ["Neon", "Chrome", "Vortex", "Zero", "Iron", "Jade", "Pulse", "Hollow",
              "Crimson", "Quantum", "Static", "Obsidian"]


def open_businesses(db):
    return db.query(Business).filter(Business.status == "open").all()


def found_business(db, agent: Agent, day: int, tick: int, rng):
    """Agent founds a business if they can afford it. Returns the Business or None."""
    if agent.wealth < MIN_WEALTH_TO_FOUND:
        return None
    btype = rng.choice(BTYPE_BY_FACTION.get(agent.faction, ["noodle_bar"]))
    
    names_pool = {
        "market_node": ["Mandi Logistics", "Neta Commercial Complex", "Bazaar Plaza"],
        "fabrication_plant": ["Tata Fabrication Works", "Mahindra Steel Hub", "Desi Casting Plant"],
        "ad_agency": ["Bollywood PR", "Desi Masala Marketing", "Jugaad Advertising"],
        "data_den": ["Bengaluru Server Room", "PG Moonlighting Cell", "Jugaad Hacker Hub"],
        "crypto_exchange": ["Desi Chit Fund", "Shadow Hawala Net", "Bengaluru Tech Exchange"],
        "net_cafe": ["Jugaad Internet Parlour", "Cyber Cafe", "Tech Park Terminal"],
        "smuggling_ring": ["Water Tanker Depot", "RTO Broker Syndicate", "Local Cab Cartel"],
        "fight_pit": ["Local Akhada Club", "Kabaddi Bet Ring", "Gully Cricket Arena"],
        "chop_shop": ["Chor Bazaar Garage", "Rickshaw Scrap Yard", "Local Auto Repair"],
        "noodle_bar": ["Sharma Sweets & Chaat", "Raju Ki Cutting Chai", "Gupta Dosa Stall"],
        "ripperdoc_clinic": ["Government Civil Clinic", "Desi Medical Store", "Ayurvedic Pharmacy"],
        "pawn_shop": ["Muthoot Gold Pawn", "Gupta Kirana Store", "Sood Jewelers & Loans"]
    }
    
    prefixes = ["Shree", "New", "Royal", "National", "Popular", "Jugaad"]
    biz_names = names_pool.get(btype, ["Cutting Chai Tapri"])
    name = f"{rng.choice(prefixes)} {rng.choice(biz_names)}"
    
    ev.append_event(db, day=day, tick=tick, type=ev.FOUND_BUSINESS, agent_id=agent.id,
                    payload={"name": name, "btype": btype, "x": agent.x, "y": agent.y}, importance=0.9)
    db.flush()
    return db.query(Business).filter(Business.owner_id == agent.id, Business.name == name, Business.status == "open").first()


def hire(db, biz: Business, day: int, tick: int, rng):
    """Hire an unemployed-ish agent into the business."""
    if len(biz.employees or []) >= 5:
        return None
    candidate = (db.query(Agent)
                   .filter(Agent.id != biz.owner_id, Agent.occupation == "unemployed")
                   .order_by(Agent.wealth.asc())
                   .first())
    if not candidate:
        candidate = (db.query(Agent)
                       .filter(Agent.id != biz.owner_id)
                       .order_by(Agent.wealth.asc())
                       .first())
    if not candidate or candidate.id in (biz.employees or []):
        return None
    ev.append_event(db, day=day, tick=tick, type=ev.HIRE, agent_id=biz.owner_id,
                    target_id=candidate.id, payload={"business": biz.name}, importance=0.7)
    db.flush()
    return candidate


def run_daily_economics(db, day: int, rng):
    """Once per day: each open business earns revenue, pays wages, maybe goes bankrupt.

    Revenue uses customer consumption events, making the economy closed-loop.
    """
    from .models import Event
    businesses = open_businesses(db)
    type_counts = {}
    for b in businesses:
        type_counts[b.btype] = type_counts.get(b.btype, 0) + 1

    # Query all CONSUME events for this day
    day_events = db.query(Event).filter(Event.day == day, Event.type == ev.CONSUME).all()
    biz_consumption = {}
    for e in day_events:
        bid = e.payload.get("business_id")
        if bid:
            biz_consumption[bid] = biz_consumption.get(bid, 0.0) + e.payload.get("amount", 0.0)

    for biz in businesses:
        owner = db.get(Agent, biz.owner_id)
        competition = type_counts.get(biz.btype, 1)

        consumption_revenue = biz_consumption.get(biz.id, 0.0)
        passive_revenue = rng.uniform(5, 15) / competition
        total_revenue = consumption_revenue + passive_revenue

        wages = WAGE * len(biz.employees or [])
        net = total_revenue - wages - RENT
        adjust = passive_revenue - wages - RENT

        ev.append_event(db, day=day, tick=0, type=ev.REVENUE, agent_id=biz.owner_id,
                        payload={"business": biz.name, "net": round(net, 1), "adjust": round(adjust, 1)},
                        importance=0.3 if net > 0 else 0.6)

        if biz.capital < 0:
            ev.append_event(db, day=day, tick=0, type=ev.BANKRUPT, agent_id=biz.owner_id,
                            payload={"business": biz.name}, importance=0.9)
