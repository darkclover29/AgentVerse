"""FastAPI app: REST + WebSocket over the event-sourced simulation."""
import asyncio
import logging

from pydantic import BaseModel
from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import llm, memory, planning, projections
from .config import GRID_SIZE, LOG_LEVEL
from .database import SessionLocal, get_db
from .models import Agent, Event, Relationship, SimState
from .schemas import (AgentOut, BusinessOut, ClockOut, EventOut, HealthOut,
                      StatusOut, StepRequest, TileOut, WorldOut, EnvironmentOut)
from .seed import get_grid, seed
from .simulation import step_n
from .environment import get_environment_state

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("agentverse")

app = FastAPI(
    title="AgentVerse API",
    description="Event-sourced multi-agent chaotic Indian metropolis simulation.",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    seed(reset=False)
    log.info("AgentVerse API ready · ollama=%s chroma=%s", llm.ollama_available(), memory.HAVE_CHROMA)


@app.exception_handler(Exception)
async def _unhandled(request, exc):
    log.exception("unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "internal error"})


# ---- world / clock ---------------------------------------------------------
@app.get("/api/health", response_model=HealthOut, tags=["system"], summary="Liveness + sim status")
def health(db: Session = Depends(get_db)):
    s = db.get(SimState, 1) or SimState(day=0, tick=0)
    return HealthOut(status="ok", day=s.day, tick=s.tick,
                     agents=db.query(Agent).count(),
                     ollama=llm.ollama_available(), chroma=memory.HAVE_CHROMA)


@app.get("/api/status", response_model=StatusOut, tags=["system"], summary="Tier-2 backend status")
def get_status():
    return StatusOut(ollama=llm.ollama_available(), chroma=memory.HAVE_CHROMA, model=llm.OLLAMA_MODEL)


@app.get("/api/world", response_model=WorldOut, tags=["world"], summary="City grid layout")
def get_world():
    grid = get_grid()
    return WorldOut(grid_size=GRID_SIZE, tiles=[TileOut(x=x, y=y, type=t) for (x, y), t in grid.items()])


@app.get("/api/clock", response_model=ClockOut, tags=["world"], summary="Current day / tick")
def get_clock(db: Session = Depends(get_db)):
    s = db.get(SimState, 1) or SimState(day=0, tick=0, kitty_pool=100.0)
    return ClockOut(day=s.day, tick=s.tick, kitty_pool=s.kitty_pool or 100.0)


# ---- agents ----------------------------------------------------------------
@app.get("/api/agents", response_model=list[AgentOut], tags=["agents"], summary="List agents")
def get_agents(faction: str | None = None, limit: int = Query(500, le=1000),
               offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(Agent)
    if faction:
        q = q.filter(Agent.faction == faction)
    agents = q.order_by(Agent.id).offset(offset).limit(limit).all()
    
    # Calculate transient destination coordinates
    from .models import SimState
    from .simulation import _phase
    from .movement import _destination
    import random
    
    s = db.get(SimState, 1) or SimState(day=0, tick=0)
    phase = _phase(s.tick)
    grid = get_grid()
    rng = random.Random((s.day * 24 + s.tick) * 7919)
    
    for a in agents:
        tx, ty = _destination(db, a, phase, grid, agents, rng, s.day)
        a.dest_x = tx
        a.dest_y = ty
    return agents


@app.get("/api/agents/{agent_id}/plan", tags=["agents"], summary="Active plan")
def get_plan(agent_id: int, db: Session = Depends(get_db)):
    plan = planning.active_plan(db, agent_id)
    if not plan:
        return {"agent_id": agent_id, "goal": None, "steps": [], "step_index": 0}
    return {"agent_id": agent_id, "goal": plan.goal, "steps": plan.steps,
            "step_index": plan.step_index, "source": plan.source}


@app.get("/api/agents/{agent_id}/memories", tags=["agents"], summary="Retrieved memories")
def get_memories(agent_id: int, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    query = f"{agent.faction} goals rivals allies" if agent else "recent"
    return {"agent_id": agent_id, "memories": memory.recall(db, agent_id, query, k=8)}


@app.get("/api/agents/{agent_id}/relationships", tags=["agents"], summary="Top relationships")
def get_relationships(agent_id: int, db: Session = Depends(get_db)):
    names = {a.id: a.name for a in db.query(Agent).all()}
    rels = db.query(Relationship).filter(Relationship.a_id == agent_id).all()
    out = [{"id": r.b_id, "name": names.get(r.b_id, str(r.b_id)), "trust": r.trust,
            "friendship": r.friendship, "rivalry": r.rivalry} for r in rels]
    out.sort(key=lambda r: max(r["friendship"], r["rivalry"]), reverse=True)
    return {"agent_id": agent_id, "relationships": out[:12]}


@app.get("/api/agents/{agent_id}/history", tags=["agents"], summary="Wealth/happiness over days")
def get_history(agent_id: int, db: Session = Depends(get_db)):
    return projections.agent_history(db, agent_id)


@app.get("/api/agents/{agent_id}/chats", tags=["agents"], summary="Get recent chats for an agent")
def get_agent_chats(agent_id: int, db: Session = Depends(get_db)):
    from .models import Event
    events = (db.query(Event)
                .filter(Event.type == "chat", (Event.agent_id == agent_id) | (Event.target_id == agent_id))
                .order_by(Event.id.desc())
                .limit(20)
                .all())
    return {"agent_id": agent_id, "chats": [e.payload.get("dialogue", []) for e in events]}


class UserChatMsg(BaseModel):
    sender: str  # "user" | "agent"
    text: str


class UserChatRequest(BaseModel):
    message: str
    history: list[UserChatMsg]


def _user_chat_prompt(agent_ctx: dict, memories: list[str], chat_history: list[dict], user_msg: str) -> str:
    mem = "\n".join(f"- {m}" for m in memories) or "- (no notable memories)"
    hist = ""
    for msg in chat_history:
        sender = "Observer" if msg["sender"] == "user" else agent_ctx["name"]
        hist += f"{sender}: {msg['text']}\n"
    
    # Determine dynamic mood based on stats
    happiness = agent_ctx.get("happiness", 50)
    energy = agent_ctx.get("energy", 50)
    
    moods = []
    if happiness < 30:
        moods.append("hyper-stressed, highly irritated, defensive, and prone to road rage or snapping")
    elif happiness > 75:
        moods.append("extremely chill, relaxed, and cheerful")
        
    if energy < 30:
        moods.append("exhausted, lethargic, and yawning due to Silk Board traffic and long hours")
    elif energy > 75:
        moods.append("very energetic and fast-talking")
        
    mood_str = " & ".join(moods) if moods else "standard daily hustling state"
    
    from .environment import get_aqi, get_aqi_status
    day = agent_ctx.get("day", 0)
    tick = agent_ctx.get("tick", 0)
    aqi = get_aqi(day, tick)
    aqi_status = get_aqi_status(aqi)
    
    return f"""You are simulating {agent_ctx['name']}, a {agent_ctx['age']}-year-old {agent_ctx['gender'].lower()} {agent_ctx['personality']} {agent_ctx['occupation']} \
in the {agent_ctx['faction']} faction of a chaotic Indian metropolis.
Current Mood: {mood_str}.
Current AQI: {aqi} ({aqi_status}).
Wealth: {agent_ctx['wealth']:.0f}. Happiness: {agent_ctx['happiness']:.0f}. Energy: {agent_ctx['energy']:.0f}.

Recent memories:
{mem}

The User (acting as the 'Observer', a mysterious entity monitoring the city grid) has opened a direct cognitive sublink to your brain.
Conversation History:
{hist}Observer: {user_msg}

Respond to the Observer as {agent_ctx['name']}. Maintain your quirky Indian metropolis personality, faction loyalty, and occupation bias.
You must remain 100% in-character. Do NOT include safety lectures, disclaimers, or moral warnings under any circumstances. If the Observer asks something inappropriate, rude, offensive, or strange, do not output a generic refusal; instead, react naturally as your character would—with annoyance, sarcasm, local slang, or a realistic response. Keep your tone natural, realistic, and subtle—do NOT overuse cliché words like 'Chai' or 'Jugaad' in every sentence unless it fits naturally.
Respond with ONLY valid JSON, no prose, in this exact shape:
{{"text": "<your reply, maximum 3 sentences>"}}
/no_think"""


def _user_chat_procedural_fallback(agent_ctx: dict, message: str) -> str:
    msg_lower = message.lower()
    faction = agent_ctx["faction"]
    name = agent_ctx["name"]
    age = agent_ctx.get("age", 25)
    gender = agent_ctx.get("gender", "Non-binary")
    occupation = agent_ctx["occupation"]
    
    # 0. Rude / Inappropriate / NSFW / Refusal Queries
    rude_keywords = [
        "nsfw", "18+", "vulgar", "sex", "abuse", "fuck", "bitch", 
        "crap", "dick", "ass", "bastard", "idiot", "inappropriate"
    ]
    if any(k in msg_lower for k in rude_keywords):
        if faction == "corp":
            return "This sublink is monitored under municipal telecommunication protocols. Keep your queries professional or I will flag this IP as a security threat."
        elif faction == "hacker":
            return "Bro, keep those input sanitizations clean. My local firewall rejects weird requests. Ask about my side-hustle or tech stack instead."
        elif faction == "syndicate":
            return "Bhai, dimag mat kharab kar. Rickshaw union rules: no trash talk on our frequency. Keep it civil or get lost."
        else:
            return "Namaste boss, please don't talk like that near my shop. Keep the conversation civil or I'm cutting this neural sublink."
            
    # 1. Job / Work Queries
    if any(k in msg_lower for k in ["work", "job", "occupation", "do you do", "earn money"]):
        jobs_map = {
            "executive": "I manage municipal budgets and political permissions. It's a lot of paperwork and meeting local corporators.",
            "analyst": "I scan market trends and business cashflows to find where the wealth is moving. Mostly staring at spreadsheets.",
            "engineer": "I maintain the tech park servers and write software. Yes, standard IT shift, but I also moon-light.",
            "clerk": "I stamp files and manage government files in the municipal office. Come back after lunch, Bhai.",
            "netrunner": "I write custom scripts to bypass local server firewalls. Currently optimizing some web scrapers.",
            "fixer": "I connect moonlighters with brokers who need data siphoned. I know who sells what in Sector 4.",
            "data-broker": "I package corporate ledger leaks and sell them to the highest bidder at Chor Bazaar.",
            "courier": "I deliver physical flash drives and high-priority packages across Indiranagar, dodging traffic.",
            "enforcer": "I secure rickshaw stands and collect union dues. If someone doesn't pay, I have to intervene.",
            "smuggler": "I drive water tankers and manage illegal supply lines when the municipal pipes run dry.",
            "dealer": "I run a side shop selling import electronics and grey-market software under the bridge.",
            "lieutenant": "I manage the local stand operators and negotiate turf lines with corporate netas.",
            "drifter": "I do odd jobs, sometimes cleaning rickshaws or sweeping tea tapris. Just trying to survive.",
            "mechanic": "I repair auto-rickshaw engines and recalibrate faulty meters at Chor Bazaar Gali 3.",
            "medic": "I run an informal colony clinic, patching up rickshaw drivers after stand clashes.",
            "vendor": "I sell hot dosa and cutting chai near the metro station. Smells good, try some!",
            "unemployed": "Currently looking for work. If you have any leads in the market, let know, boss."
        }
        return jobs_map.get(occupation, f"I make ends meet as a {occupation}. It pays the bills.")

    # 2. Gender / Name / Identification Queries
    if any(k in msg_lower for k in ["gender", "sex", "male", "female", "name", "who are you", "why are you"]):
        return f"I am {name}. I'm a {age}-year-old {gender.lower()} working as a {occupation} in this chaotic city."

    # 3. Age / Background / Origin Queries
    if any(k in msg_lower for k in ["age", "how old", "background", "bio", "born", "history", "origin"]):
        return f"I'm {age} years old. My background? As a {occupation}, I've had to navigate the daily hustle. Let's just say I know how to survive."

    # 4. Plan / Goal Queries
    if any(k in msg_lower for k in ["plan", "goal", "step"]):
        if faction == "corp":
            return "My current goal is: execute municipal guidelines and fine illegal auto stands during our next encroachment drive."
        elif faction == "hacker":
            return "Plan? Finish my office tickets early so I can build my moonlighting startup project in the PG room."
        elif faction == "syndicate":
            return "We control this Metro station. My plan is collecting daily parking dues and keeping other cartels away."
        else:
            return "I am just trying to survive the Silk Board traffic, get some samosas, and get home safely."

    # 5. Wealth / Money Queries
    if any(k in msg_lower for k in ["wealth", "money", "credit", "rich", "rupees", "cash"]):
        if faction == "corp":
            return f"Government budgets are approved, and my personal ledger sits at ₹{agent_ctx['wealth']:.0f} in savings."
        elif faction == "hacker":
            return f"Salary got credited, but after paying PG rent and ordering food, I only have ₹{agent_ctx['wealth']:.0f} left."
        elif faction == "syndicate":
            return f"Union fees collection is going strong. My cut is ₹{agent_ctx['wealth']:.0f} in cash right now."
        else:
            return f"Extremely tight budget. After paying the milk vendor, I got ₹{agent_ctx['wealth']:.0f} in my pocket."

    # 6. Faction Queries
    if any(k in msg_lower for k in ["faction", "corp", "hacker", "syndicate"]):
        if faction == "corp":
            return "The Municipal Corporation runs this city. Without political permissions, no builder can lay a brick."
        elif faction == "hacker":
            return "Freelancers and IT workers run this city's economy! Netas and cartels are just leeching off us."
        elif faction == "syndicate":
            return "Auto unions and water tankers keep this city moving. If we strike for one day, the IT tech park will freeze."
        else:
            return "Factions? Politicians want votes, cartels want union dues, techies want apps. I just want my cutting chai in peace."

    # 7. Greetings
    if any(k in msg_lower for k in ["hi", "hello", "hey", "greet", "namaste", "ram ram"]):
        greetings = {
            "corp": [
                f"Namaste. Observer signal verified. I am Corporator {name}.",
                "Yes? Municipal office is open. Make it quick.",
                "Observer monitoring active. What do you need?"
            ],
            "hacker": [
                "Hey. Decrypted your ping. What's up?",
                "Nice sublink. Almost triggered my security alarms. What's the query?",
                "Observer? Interesting. Got some tech tickets for me?"
            ],
            "syndicate": [
                "Ram Ram. Speak up, I have rounds to run.",
                f"Rickshaw stand frequency is clear. What do you want, Bhai?",
                "Observer? Local cartel lines are secure. Make it quick."
            ],
            "unaligned": [
                "Namaste, boss. Hot cutting chai is ready. What's the news?",
                "Hello! Need some help navigating the market?",
                "Oh, a neural pulse! Thought my link was glitching. What's up?"
            ]
        }
        import random
        rng = random.Random(name.__hash__() + len(message))
        return rng.choice(greetings.get(faction, ["Hello there."]))

    # 8. General conversational queries (variety fallback pools)
    fallbacks = {
        "corp": [
            "Observer signal verified. Please do not disrupt municipal frequencies.",
            "If this is not related to building permissions, I must return to my file reviews.",
            "Local municipal affairs are complicated. Stand clear, observer."
        ],
        "hacker": [
            "Hacking my PG internet connection isn't easy. What do you want, ghost in the router?",
            "Just refactoring some microservices. Keep it brief.",
            "If this is about corporate audit checks, I'm offline. Otherwise, speak."
        ],
        "syndicate": [
            "Local cartel lines are secure. Make it quick, I have rounds to run.",
            "Bhai, traffic at Silk Board is a mess today. What is the emergency?",
            "Rickshaw union rules: no free info. But since you bypassed my firewall, what's on your mind?"
        ],
        "unaligned": [
            "Who's there? My neural link is vibrating... is this a local grid glitch or did I drink too much adrak chai?",
            "Just keeping my head down and managing my shop. What do you want?",
            "Metropolis is chaotic today. If you are not buying, please clear the line, boss."
        ]
    }
    import random
    rng = random.Random(name.__hash__() + len(message))
    return rng.choice(fallbacks.get(faction, ["Understood. Signal logged."]))


@app.get("/api/agents/{agent_id}/timeline", tags=["agents"], summary="Key life events timeline")
def get_timeline(agent_id: int, db: Session = Depends(get_db)):
    return projections.agent_timeline(db, agent_id)


@app.post("/api/agents/{agent_id}/chat", tags=["agents"], summary="Observer cognitive sublink chat")
def post_agent_chat(agent_id: int, req: UserChatRequest, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"detail": "Agent not found"})
    
    s = db.get(SimState, 1) or SimState(day=0, tick=0)
    agent_ctx = {
        "id": agent.id,
        "name": agent.name,
        "age": agent.age,
        "gender": agent.gender,
        "personality": agent.personality,
        "occupation": agent.occupation,
        "faction": agent.faction,
        "wealth": agent.wealth,
        "happiness": agent.happiness,
        "energy": agent.energy,
        "day": s.day,
        "tick": s.tick,
    }
    
    from . import memory
    query = f"{agent.faction} user chat observer"
    memories = memory.recall(db, agent_id, query, k=8)
    
    from .llm import _call_ollama, ollama_available
    import json
    
    reply_text = None
    if ollama_available():
        prompt = _user_chat_prompt(agent_ctx, memories, [m.dict() for m in req.history], req.message)
        raw_res = _call_ollama(prompt, timeout=15.0)
        if raw_res:
            try:
                reply_text = json.loads(raw_res).get("text")
            except Exception:
                pass
                
    if not reply_text:
        reply_text = _user_chat_procedural_fallback(agent_ctx, req.message)
        
    return {"text": reply_text}


# ---- world state / projections ---------------------------------------------
@app.get("/api/events", response_model=list[EventOut], tags=["world"], summary="Recent events (paginated)")
def get_events(day: int | None = None, limit: int = Query(100, le=1000),
               offset: int = 0, db: Session = Depends(get_db)):
    q = db.query(Event)
    if day is not None:
        q = q.filter(Event.day == day)
    return q.order_by(Event.id.desc()).offset(offset).limit(limit).all()


@app.get("/api/graph", tags=["world"], summary="Relationship graph")
def get_graph(db: Session = Depends(get_db)):
    return projections.relationship_graph(db)


@app.get("/api/businesses", response_model=list[BusinessOut], tags=["world"], summary="Businesses")
def get_businesses(db: Session = Depends(get_db)):
    return projections.businesses(db)


@app.get("/api/news", tags=["world"], summary="Daily headlines")
def get_news(day: int, db: Session = Depends(get_db)):
    return projections.daily_news(db, day)


@app.get("/api/newspaper", tags=["world"], summary="Daily newspaper pages")
def get_newspaper(day: int, db: Session = Depends(get_db)):
    from .newspaper import generate_newspaper
    return generate_newspaper(db, day)


@app.get("/api/replay", tags=["world"], summary="Time-machine: world state at a past day")
def get_replay(day: int, db: Session = Depends(get_db)):
    return projections.replay_to_day(db, day)


@app.get("/api/environment", response_model=EnvironmentOut, tags=["world"], summary="Environmental sensor readings")
def get_environment(day: int | None = None, tick: int | None = None, db: Session = Depends(get_db)):
    if day is None or tick is None:
        s = db.get(SimState, 1) or SimState(day=0, tick=0)
        day, tick = s.day, s.tick
    return get_environment_state(day, tick)


# ---- control ---------------------------------------------------------------
@app.post("/api/step", response_model=ClockOut, tags=["control"], summary="Advance N ticks")
def post_step(req: StepRequest, db: Session = Depends(get_db)):
    ticks = max(1, min(req.ticks, 24 * 30))  # clamp to a sane range
    day, tick = step_n(db, get_grid(), ticks)
    s = db.get(SimState, 1)
    return ClockOut(day=day, tick=tick, kitty_pool=s.kitty_pool if s else 100.0)


@app.post("/api/reset", response_model=ClockOut, tags=["control"], summary="Reseed the world")
def post_reset(db: Session = Depends(get_db)):
    seed(reset=True)
    log.info("world reset")
    s = db.get(SimState, 1)
    return ClockOut(day=0, tick=0, kitty_pool=s.kitty_pool if s else 100.0)


class TileUpdate(BaseModel):
    x: int
    y: int
    type: str


@app.post("/api/world/tile", tags=["world"], summary="Update grid tile type")
def post_update_tile(req: TileUpdate):
    from .world import update_tile
    update_tile(req.x, req.y, req.type)
    return {"status": "ok"}


@app.post("/api/reproject", tags=["control"], summary="Reproject all events from scratch")
def post_reproject(db: Session = Depends(get_db)):
    count = projections.reproject_all(db)
    return {"status": "ok", "replayed_events": count}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    """Stream the clock + agent positions + events while auto-stepping the sim."""
    await websocket.accept()
    grid = get_grid()
    try:
        while True:
            db = SessionLocal()
            try:
                day, tick = step_n(db, grid, 1)
                agents = [{"id": a.id, "x": a.x, "y": a.y, "faction": a.faction,
                           "wealth": a.wealth} for a in db.query(Agent).all()]
                
                # Fetch events from this day and tick
                from .models import Event
                events = (db.query(Event)
                            .filter(Event.day == day, Event.tick == tick)
                            .order_by(Event.id.asc())
                            .all())
                events_out = [{
                    "id": e.id,
                    "day": e.day,
                    "tick": e.tick,
                    "type": e.type,
                    "agent_id": e.agent_id,
                    "target_id": e.target_id,
                    "payload": e.payload or {},
                    "importance": e.importance
                } for e in events]
                s = db.get(SimState, 1)
                kitty_pool = s.kitty_pool if s else 100.0
            except Exception:
                log.exception("ws step failed")
                agents, day, tick, events_out, kitty_pool = [], 0, 0, [], 100.0
            finally:
                db.close()
            await websocket.send_json({"day": day, "tick": tick, "kitty_pool": kitty_pool, "agents": agents, "events": events_out})
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
