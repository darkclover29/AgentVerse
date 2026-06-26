"""AI-Generated and Procedural Newspaper Generator for The Metropolitan Samachar."""
import json
import random
from sqlalchemy.orm import Session
from .models import Agent, Event, Business
from .llm import _call_ollama, ollama_available
from . import events as ev

# Indian Metropolis ads database
CYBER_ADS = [
    {"title": "RAJU JUGAAD MOBILES", "tagline": "Upgrade your screen, fix that software!", "desc": "15% off mobile screen replacement this week. Sector 4 Market Gali."},
    {"title": "RAJU KI CHAI TAPRI", "tagline": "Real ginger, fresh milk, hot samosas.", "desc": "Try our new Adrak Special Chai. Now with hot crispy samosas!"},
    {"title": "GUPTA RICKSHAW REPAIRS", "tagline": "Broken meter? Sputtering engine?", "desc": "We get your auto back on the street. Fast Jugaad, no questions asked."},
    {"title": "WANTED: SCRAP METAL & PHONES", "tagline": "Highest rates paid for old copper & devices.", "desc": "Drop off at Chor Bazaar, Gali 3. Cash paid immediately."},
    {"title": "MAHESH CHIT FUND", "tagline": "Save monthly, double your investment.", "desc": "Fully trustable local chit scheme. Easy withdrawals, safe and secure."},
    {"title": "RAMBO SECURITY SERVICES", "tagline": "Because these streets can be wild.", "desc": "Strong guards for shops & events. Bulletproof vests on rent. ₹199/hr."},
    {"title": "LONAVALA RETREAT RESORT", "tagline": "Escape the traffic and gridlock of the city.", "desc": "Real grass! Fresh air! Booking rooms for monsoon season. Apply within."},
    {"title": "DESI PET CORNER", "tagline": "Playful, clean, trained street puppies.", "desc": "Adopt friendly local street dogs. Vet checks and vaccine cards guaranteed."}
]

def generate_newspaper(db: Session, day: int) -> dict:
    """Generate the structured newspaper dictionary for the given day."""
    # 1. Fetch events of the day
    day_events = (
        db.query(Event)
        .filter(Event.day == day)
        .order_by(Event.importance.desc(), Event.id.asc())
        .all()
    )
    
    # 2. Get agent names mapping
    names = {a.id: a.name for a in db.query(Agent).all()}
    
    # 3. Compile brief bulletins for "City Wire"
    bulletins = []
    gossip = []
    
    for e in day_events:
        actor = names.get(e.agent_id, f"Agent {e.agent_id}")
        target = names.get(e.target_id, "")
        p = e.payload or {}
        
        # Wire bulletins
        if e.type == ev.FOUND_BUSINESS:
            bulletins.append(f"BREAKING: {actor} opened new venture '{p.get('name')}' in Block {random.randint(1,9)}.")
        elif e.type == ev.BANKRUPT:
            bulletins.append(f"LIQUIDATION: '{p.get('business')}' collapsed due to zero capital. Owner {actor} bankrupted.")
        elif e.type == ev.DATA_HEIST:
            bulletins.append(f"HEIST: Moonlighter {actor} siphoned ₹{p.get('amount')} from {p.get('business_name')}.")
        elif e.type == ev.SHAKEDOWN:
            bulletins.append(f"EXTORTION: Auto union leader {actor} extorted ₹{p.get('amount')} from {p.get('business_name')}.")
        elif e.type == ev.LOCKDOWN:
            bulletins.append(f"LOCKDOWN: Municipal officers fined {p.get('business_name')} ₹{p.get('amount')} during encroachment drive.")
        elif e.type == ev.MUTUAL_AID:
            bulletins.append(f"AID: Mohalla committee fund transferred ₹{p.get('amount')} to support {p.get('business_name')}.")
            
        # Gossip column (from chats and betrayals)
        if e.type == "chat":
            dialogue = p.get("dialogue", [])
            first_line = dialogue[0]["text"] if dialogue else "..."
            gossip.append(f"OVERHEARD: {actor} was spotted talking with {target}. Whispers: \"{first_line[:50]}...\"")
        elif e.type == ev.BETRAY:
            gossip.append(f"BETRAYAL: Local colony rumors indicate a major rift between {actor} and {target}. A retaliation plan is rumored.")
        elif e.type == ev.HELP:
            gossip.append(f"ALLIANCE: Neighbors report {actor} helped {target} pay the local milk supplier. Friendship index rising.")

    # Dedup and limit lists
    bulletins = list(dict.fromkeys(bulletins))[:6]
    gossip = list(dict.fromkeys(gossip))[:4]
    
    # Fill empty lists with default city life reports
    if not bulletins:
        bulletins = [
            "TRAFFIC: Silk Board flyover block stabilized at 45 minutes.",
            "WEATHER: Heavy water logging at Railway Underpass. Avoid route.",
            "ALERT: Municipal corporation drives increased in market zones.",
            "MARKET: Onion prices up 5% due to transit supply delays."
        ]
    if not gossip:
        gossip = [
            "RUMOR: Sector 3 auto stand planning a sudden transport strike.",
            "SIGHTING: Mysterious black SUV with VIP horns seen near local office park.",
            "CHITCHAT: IT workers complaining about night-shift moonlighting inspections."
        ]

    # 4. Generate Main Articles (via LLM if available, otherwise procedural fallback)
    articles = None
    if ollama_available() and len(day_events) > 0:
        events_summary = []
        for e in day_events[:12]: # limit input context
            actor = names.get(e.agent_id, f"Agent {e.agent_id}")
            target = names.get(e.target_id, "")
            p = e.payload or {}
            events_summary.append(f"Type: {e.type}, Actor: {actor}, Target: {target}, Details: {p}")
            
        prompt = f"""You are the editor-in-chief of "The Metropolitan Samachar", a sensational local tabloid in a chaotic Indian Metropolis.
Here are the key events that occurred on Day {day}:
{chr(10).join(events_summary)}

Write the front page stories for Day {day} of the simulation.
Respond with ONLY valid JSON, no prose, in this exact shape:
{{
  "headline": {{
    "title": "<capitalized sensationalized headline about the most important event>",
    "body": "<2-3 paragraph detailed news story in dramatic local Indian newspaper style>",
    "author": "<cool local Indian reporter name>"
  }},
  "faction_news": {{
    "title": "<headline about corporate tech earnings, Moonlighting techies, or Auto union turf wars>",
    "body": "<1-2 paragraph news story about faction power struggles>",
    "author": "<specialist reporter name>"
  }},
  "opinion": {{
    "title": "<cynical editorial headline about the state of traffic/city>",
    "body": "<1-2 paragraph highly cynical editorial comment>",
    "author": "<cynical op-ed columnist name>"
  }}
}}
/no_think"""
        
        raw_res = _call_ollama(prompt, timeout=15.0)
        if raw_res:
            try:
                articles = json.loads(raw_res)
            except Exception:
                pass
                
    if not articles:
        articles = _procedural_articles(day, day_events, names)

    # 5. Generate weather and classifieds
    rng_val = (day * 137) % 100
    weather = {
        "acid_rain": f"{15 + (rng_val % 45)}%",
        "smog_density": f"{50 + (rng_val * 7 % 45)}%",
        "grid_latency": f"{35 + (rng_val % 40)} min",
        "advisory": "Heavy Monsoons Expected. Carry umbrellas and avoid underpasses." if rng_val % 2 == 0 else "Severe Smog and dust storm warnings active. Mask up."
    }
    
    # Pick 3 random ads based on day seed
    rng = random.Random(day * 997)
    classifieds = rng.sample(CYBER_ADS, 3)

    # 6. Construct structured pages
    return {
        "day": day,
        "edition": f"Vol. {100 + day}, No. {day}",
        "date": f"June 24, 2026",
        "weather": weather,
        "pages": [
            {
                "id": "front",
                "title": "Front Page",
                "articles": [
                    {
                        "type": "headline",
                        "title": articles["headline"]["title"],
                        "body": articles["headline"]["body"],
                        "author": articles["headline"]["author"]
                    }
                ],
                "bulletins": bulletins
            },
            {
                "id": "factions",
                "title": "Metapolitics",
                "articles": [
                    {
                        "type": "faction",
                        "title": articles["faction_news"]["title"],
                        "body": articles["faction_news"]["body"],
                        "author": articles["faction_news"]["author"]
                    }
                ],
                "ads": classifieds
            },
            {
                "id": "scandals",
                "title": "Local Scandals",
                "articles": [
                    {
                        "type": "opinion",
                        "title": articles["opinion"]["title"],
                        "body": articles["opinion"]["body"],
                        "author": articles["opinion"]["author"]
                    }
                ],
                "gossip": gossip
            }
        ]
    }

def _procedural_articles(day: int, events: list, names: dict) -> dict:
    """Generate generic template-based local news when LLM is unavailable."""
    heist = next((e for e in events if e.type == ev.DATA_HEIST), None)
    lockdown = next((e for e in events if e.type == ev.LOCKDOWN), None)
    shakedown = next((e for e in events if e.type == ev.SHAKEDOWN), None)
    bankrupt = next((e for e in events if e.type == ev.BANKRUPT), None)
    found = next((e for e in events if e.type == ev.FOUND_BUSINESS), None)

    headline = {}
    faction = {}
    opinion = {}

    # Lead Headline Article
    if heist:
        h_actor = names.get(heist.agent_id, "Unknown Moonlighter")
        h_biz = heist.payload.get("business_name", "a corporate server")
        h_amt = heist.payload.get("amount", 0)
        headline = {
            "title": f"MOONLIGHTING SCAM: TECHIE SIPHONS ₹{h_amt} FROM {h_biz.upper()}",
            "body": f"The tech park was rocked today as junior developer {h_actor} was found to have siphoned ₹{h_amt} in freelancing payments directly from {h_biz}. "
                    f"Sources confirm that corporate HR detected the moonlighting telemetry post-transaction. Over ₹{h_amt} in client payments was routed to personal bank accounts. "
                    f"Moonlighting techies are celebrating the breach, while corporate security teams declined to comment. 'It was a simple Jugaad,' said a local developer.",
            "author": "Tech Khabri"
        }
    elif bankrupt:
        b_actor = names.get(bankrupt.agent_id, "A local merchant")
        b_biz = bankrupt.payload.get("business", "a street stall")
        headline = {
            "title": f"STREET DISSOLUTION: {b_biz.upper()} COLLAPSES UNDER PRESSURE",
            "body": f"The brutal economics of the Indian metropolis has claimed another victim. Local shop '{b_biz}' shut its doors permanently today due to lack of capital. "
                    f"Owner {b_actor} has reportedly sold off all shop inventory to clear credit debts. Neighbors spoke of the sudden closure with sadness: 'One day they are serving cutting chai, the next day municipal officers seal it.' "
                    f"Local committees warn this represents a systemic drain on independent street vendor sectors.",
            "author": "Sanjay Sharma"
        }
    elif lockdown:
        l_actor = names.get(lockdown.agent_id, "Authority Officer")
        l_biz = lockdown.payload.get("business_name", "a local shop")
        l_amt = lockdown.payload.get("amount", 0)
        headline = {
            "title": f"ENCROACHMENT DRIVE: AUTHORITY FINES {l_biz.upper()}",
            "body": f"Municipal Corporation squads raided '{l_biz}' today during an encroachment drive on illegal road expansion. "
                    f"Officer {l_actor} oversaw the operation, issuing spot fines of ₹{l_amt} for blocking pedestrian footpaths. "
                    f"The venue was temporarily sealed. Local merchants claim the drive was politically motivated: 'It is a selective shakedown, pure and simple, just dressed up as authority rules.'",
            "author": "Rakesh Pandey"
        }
    elif shakedown:
        s_actor = names.get(shakedown.agent_id, "Auto Union leader")
        s_biz = shakedown.payload.get("business_name", "a street food vendor")
        s_amt = shakedown.payload.get("amount", 0)
        headline = {
            "title": f"UNION FEES: AUTO CARTEL EXTORTS ₹{s_amt} FROM {s_biz.upper()}",
            "body": f"Cartel leader {s_actor} paid a visit to '{s_biz}' today to collect union fees. "
                    f"Reports indicate that the owner paid ₹{s_amt} in cash as part of an ongoing 'monthly parking protection fee.' "
                    f"Local police turned a blind eye to the transaction. Security analysts suggest that auto cartels are rapidly expanding their control, dominating parking ranks near the metro junction.",
            "author": "Vijay Mishra"
        }
    elif found:
        f_actor = names.get(found.agent_id, "A local merchant")
        f_biz = found.payload.get("name", "a new shop")
        headline = {
            "title": f"NEW INAUGURATION: {f_biz.upper()} OPENS WITH COCONUT BREAKING",
            "body": f"A brand new shop has opened in the neighborhood. '{f_biz}', founded by local resident {f_actor}, officially broke a coconut today to mark the inauguration. "
                    f"The venture aims to provide essential goods to local residents. Customers queued outside for hot tea and sweets. "
                    f"In a city dominated by startup apps, local brick-and-mortar shops face a hard road, but {f_actor} is confident of survival.",
            "author": "Sanjay Sharma"
        }
    else:
        headline = {
            "title": "METROPOLIS INACTION: SILK BOARD TRAFFIC NORMAL",
            "body": "Traffic readouts indicate standard levels of vehicle congestion and monsoon water logging today. "
                    "Sector police reported no major strikes, auto protests, or shop shutdowns. Metro trains ran with standard 99.8% punctuality. "
                    "Commuters are advised to keep their umbrellas ready as monsoon clouds gather over the western suburbs.",
            "author": "Priya Sen"
        }

    # Faction News
    if heist or bankrupt or lockdown or shakedown:
        faction = {
            "title": "METROPOLIS WARS: CARTELS VS AUTHORITY",
            "body": "As techies moon-light and municipal officers execute encroachment fines, the balance of power in the sector is shifting. "
                    "Freelance coders claim they are fighting to clear their PG debts, while municipal officers maintain that encroachment fines are necessary for pedestrian movement. "
                    "Meanwhile, auto cartels continue to tax local unaligned businesses, further squeezing the working class.",
            "author": "Sneha Nair"
        }
    else:
        faction = {
            "title": "TECH APIS & FLAT WAGES AT METRO JCTION",
            "body": "Financial analysts report that local startups have raised new rounds of VC funds. "
                    "Street workers, however, continue to report flat wage rates despite a 5% rise in tea leaf and LPG prices. "
                    "Underground moonlighting networks are rumored to be pooling funds to support freshers struggling with local PG deposits.",
            "author": "Sneha Nair"
        }

    # Opinion column
    opinions = [
        "Are we citizens or just Excel sheet compilers? Every day we trade our happiness for a few rupees, only to spend it on auto fares and cutting chai. The tech park wins, we lose.",
        "They tell us the water logging is just temporary monsoon rain, but my wet shoes beg to differ. If the municipal corporation won't clear the drains, local residents will eventually protest.",
        "The Netas call it 'encroachment fine', the cartels call it 'union dues', the moonlighters call it 'side-hustle'. On the streets, it all looks the same: someone in power taking money from someone who doesn't have it.",
        "Mohalla committee mutual aid is the only thing keeping this neighborhood from eating itself alive. In a world where a local tea shop goes bankrupt in a week, trust is the only asset that doesn't depreciate."
    ]
    opinion = {
        "title": f"VOICE FROM THE CHAWL: COLUMN {day}",
        "body": opinions[day % len(opinions)],
        "author": "The Desi Cynic"
    }

    return {"headline": headline, "faction_news": faction, "opinion": opinion}
