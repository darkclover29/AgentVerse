"""Agent generation + Tier-1 rule-based behavior (no LLM)."""
import random

from .config import NUM_AGENTS
from .models import Agent

FACTIONS = ["corp", "hacker", "syndicate", "unaligned"]
PERSONALITIES = ["ambitious", "cautious", "ruthless", "loyal", "curious", "reckless"]
OCCUPATIONS = {
    "corp": ["executive", "analyst", "engineer", "clerk"],
    "hacker": ["netrunner", "fixer", "data-broker", "courier"],
    "syndicate": ["enforcer", "smuggler", "dealer", "lieutenant"],
    "unaligned": ["drifter", "mechanic", "medic", "vendor", "unemployed"],
}
MALE_NAMES = ["Aarav", "Vihaan", "Aditya", "Arjun", "Kabir", "Rohan", "Siddharth", "Rahul",
              "Amit", "Vikram", "Raj", "Sai", "Ishaan", "Dev", "Yash", "Karan"]
FEMALE_NAMES = ["Neha", "Priya", "Ananya", "Aanya", "Diya", "Riya", "Kavya", "Pooja",
                "Meera", "Shruti", "Tanvi", "Sanya", "Ishita", "Aditi", "Kirti", "Kiran"]
LAST = ["Sharma", "Patel", "Verma", "Gupta", "Kumar", "Singh", "Joshi", "Reddy",
        "Mehta", "Nair", "Rao", "Iyer", "Das", "Sen", "Mishra", "Kapoor", "Bahl"]


def _generate_background(rng, name, age, gender, faction, occupation, personality):
    pronoun_sub = {"Male": "He", "Female": "She", "Non-binary": "They"}[gender]
    possessive_sub = {"Male": "His", "Female": "Her", "Non-binary": "Their"}[gender]
    
    origins = {
        "corp": [
            f"Born in the premium society flats of Indiranagar to high-ranking netas, {name} was groomed for corporate leadership.",
            f"Raised in strict coaching centres and premier engineering colleges, {name} learned early that optimization is everything.",
            f"Born to lower-middle-class clerical staff in the government quarters, {name} had to fight for every promotion in the IT park."
        ],
        "hacker": [
            f"Orphaned in the narrow lanes of Sector 4 market, {name} learned programming from local cyber cafe hackers.",
            f"A self-taught coding prodigy from the outskirts, {name} was building Android apps before buying a smartphone.",
            f"Discovered in illegal PG hostel gaming basements, {name} has spent life dodging tech park audit checks."
        ],
        "syndicate": [
            f"Hardened near the Silk Board flyovers, {name} started running errands for local water tanker cartels at age twelve.",
            f"Rebelling against a strict corporate family in South Delhi, {name} fled to the local bazaar to run cab union routes.",
            f"Born in a crowded local clinic, {name} joined rickshaw stand unions to survive the transport cartel wars."
        ],
        "unaligned": [
            f"Born to independent street vendor families near the metro station, {name} grew up surrounded by massive city traffic.",
            f"Raised in PG rooms and local tea stalls, {name} has always lived between the cracks of netas and cartels.",
            f"Grew up on the outer boundary of the metropolis, learning to keep their head down and avoid political enforcers."
        ]
    }
    
    motivations = {
        "ambitious": f"Driven by intense ambition, {pronoun_sub.lower()} views the metropolis as a ladder to be climbed at all costs.",
        "cautious": f"Extremely cautious, {pronoun_sub.lower()} keeps a low profile, saving rupees and avoiding transport cartel crossfire.",
        "ruthless": f"Hardened and ruthless, {pronoun_sub.lower()} believes that the only way to survive the bazaar is to strike first.",
        "loyal": f"Fiercely loyal, {pronoun_sub.lower()} places trust in neighborhood friends and coordinates with local union leaders.",
        "curious": f"Possessing a restless, curious mind, {pronoun_sub.lower()} spends hours scanning encrypted database logs for market secrets.",
        "reckless": f"Reckless by nature, {pronoun_sub.lower()} lives day-to-day, making high-stakes deals at the tea tapri and spending rupees fast."
    }
    
    present = f"Currently working as a {occupation}, {pronoun_sub.lower()} navigates the daily hustle of the chaotic city."
    
    origin = rng.choice(origins[faction])
    motivation = motivations[personality]
    
    return f"{origin} {motivation} {present}"


def generate_agents(grid, seed=42, n=NUM_AGENTS):
    rng = random.Random(seed)
    hab_blocks = [xy for xy, t in grid.items() if t == "hab_block"]
    agents = []
    for i in range(1, n + 1):
        faction = rng.choices(FACTIONS, weights=[3, 2, 2, 4])[0]
        occ = rng.choice(OCCUPATIONS[faction])
        home = rng.choice(hab_blocks)
        gender = rng.choices(["Male", "Female", "Non-binary"], weights=[45, 45, 10])[0]
        if gender == "Male":
            first = rng.choice(MALE_NAMES)
        elif gender == "Female":
            first = rng.choice(FEMALE_NAMES)
        else:
            first = rng.choice(MALE_NAMES + FEMALE_NAMES)
        name = f"{first} {rng.choice(LAST)}"
        age = rng.randint(18, 65)
        pers = rng.choice(PERSONALITIES)
        bg = _generate_background(rng, name, age, gender, faction, occ, pers)
        
        agents.append(Agent(
            id=i,
            name=name,
            age=age,
            gender=gender,
            background=bg,
            personality=pers,
            occupation=occ,
            faction=faction,
            wealth=float(rng.randint(20, 300)),
            happiness=float(rng.randint(30, 70)),
            energy=100.0,
            x=home[0], y=home[1],
            tier=1,
        ))
    # Promote 5 named agents to Tier-2 (LLM planners, wired up in a later milestone).
    for a in rng.sample(agents, 5):
        a.tier = 2
    return agents


# ---- Tier-1 decision logic -------------------------------------------------

def decide_action(agent: Agent, phase: str, grid, rng):
    """Return an (event_type, kwargs) tuple describing what the agent does this tick.

    phase is one of: work, social, personal, sleep. Pure logic, deterministic given rng.
    """
    if phase == "sleep":
        return ("sleep", {})

    if agent.energy < 20:
        return ("sleep", {})

    if phase == "work":
        if agent.occupation == "unemployed":
            return ("job_change", {"occupation": _find_job(agent, rng)})
        income = _income_for(agent, rng)
        return ("work", {"amount": income, "happiness": rng.choice([0, 0, 1, 2])})

    if phase == "social":
        return ("socialize", {})  # target chosen by engine (a nearby agent)

    # personal goal phase
    if agent.wealth < 50:
        return ("earn", {"amount": float(rng.randint(5, 20))})
    return ("socialize", {})


def _income_for(agent: Agent, rng):
    base = {
        "executive": 40, "analyst": 22, "engineer": 25, "clerk": 12,
        "netrunner": 35, "fixer": 30, "data-broker": 28, "courier": 14,
        "enforcer": 20, "smuggler": 32, "dealer": 24, "lieutenant": 38,
        "drifter": 6, "mechanic": 16, "medic": 20, "vendor": 14, "unemployed": 0,
    }.get(agent.occupation, 12)
    return float(base + rng.randint(-3, 5))


def _find_job(agent: Agent, rng):
    return rng.choice([o for o in OCCUPATIONS[agent.faction] if o != "unemployed"])
