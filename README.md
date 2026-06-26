# AgentVerse

A self-evolving cyberpunk megacity where autonomous agents live, work, form relationships,
and generate emergent stories. Event-sourced simulation backend (FastAPI) + live React
dashboard with a Time Machine.

See [`AGENTVERSE_PLAN.md`](./AGENTVERSE_PLAN.md) for the full architecture and roadmap.

## Layout

```
backend/    FastAPI · SQLAlchemy · event-sourced sim engine
frontend/   React + Vite dashboard (city grid, news feed, timeline)
```

## Quick start (Windows)

Double-click **`start.bat`** (or run it from a terminal). It sets up the backend venv +
dependencies, seeds the city on first run, installs frontend deps, launches both servers
in their own windows, and opens the dashboard. Close the two windows to stop.

Manual setup below if you prefer.

## Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed                  # create DB + 100 agents + city grid
uvicorn app.main:app --reload       # http://localhost:8000  (docs at /docs)
```

SQLite is used by default (zero setup). To use Postgres, set
`DATABASE_URL=postgresql+psycopg://user:pass@localhost/agentverse`. Config can also live
in a `backend/.env` file (see `.env.example`).

Run the tests:

```bash
cd backend && pytest
```

## Run the frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173 (proxies /api + /ws to :8000)
```

Click **Run** to auto-step the simulation, **Step** to advance manually, and drag the
**Time Machine** slider to replay the city's state at any past day.

## How it works (event sourcing)

Every action an agent takes is an immutable `Event` appended to the store. World state,
the relationship graph, and daily news are all *projections* folded from that event
stream — so replaying events up to day N reconstructs the world exactly as it was. That's
the whole Time Machine.

## Tier-2 AI agents (optional, with fallbacks)

5 named agents are LLM planners. Each generates a multi-day **plan** (a goal + ordered
steps from a fixed action vocabulary) that the engine executes over many ticks. Before
planning, the agent retrieves relevant **memories** of its own past (RAG) to ground the
prompt. Plans, memories, and relationships are all visible in the agent detail panel
(click any agent).

The whole thing runs with or without the optional stack:

| Component | If installed | Fallback |
|-----------|--------------|----------|
| **Ollama** (`ollama pull qwen3:8b`) | LLM-generated goals + steps | Heuristic faction-based planner |
| **ChromaDB** (`pip install chromadb`) | Semantic vector memory | Keyword + recency + importance scoring |

The `/api/status` endpoint and the dashboard header badge show which mode is active.
Set `OLLAMA_MODEL` to use a different model (e.g. `deepseek-r1:8b`).

## Current status

- ✅ Event store + projections (Agent, Relationship, Plan)
- ✅ 20×20 grid, 100 agents, 4 factions, Tier-1 rule behavior
- ✅ Tick loop (24 ticks/day), daily phases
- ✅ REST API + WebSocket live stream
- ✅ React dashboard: city grid, news feed, timeline replay
- ✅ Force-directed relationship graph view
- ✅ Tier-2 LLM planners (Ollama) with heuristic fallback
- ✅ Vector memory (ChromaDB) with keyword fallback
- ✅ Non-blocking planning: LLM runs in a background thread pool, so the tick loop never stalls
- ✅ Test suite (pytest) + GitHub Actions CI; `/api/health`, logging, paginated endpoints
- ✅ Agent detail panel: plan, memories, relationships, wealth/happiness sparklines
- ✅ Economy: agents found businesses, hire staff, earn revenue, go bankrupt under competition
- ✅ Animated agent movement (agents commute to work / seek others / go home)
- ✅ Primed-rivalry seed scenario for a dramatic opening
- ⬜ Demo GIF + screenshots in README

## Economy

Tier-2 agents with enough capital can **found a business** (type depends on faction:
corp → market nodes / fab plants, hacker → data dens / exchanges, syndicate →
smuggling rings / fight pits). Businesses **hire** the poorest agents, earn daily
**revenue** split by local competition, pay **wages + rent**, and **go bankrupt** when
saturated markets can't cover overhead — laying off their staff. It all flows through the
event stream, so business births and deaths show up in the news feed and the Time Machine.

Businesses appear as amber diamonds on the city grid; the HUD shows the live firm count.
```

