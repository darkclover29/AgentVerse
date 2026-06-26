# AgentVerse — Revised Build Plan

A self-evolving cyberpunk megacity where autonomous agents form relationships, pursue
goals, and generate emergent stories. Portfolio focus: **agent intelligence + system
design + visualization**. No ML models (avoids the "model just relearns my own rules"
trap); the depth comes from emergent behavior, memory, and clean architecture.

---

## What changed from the original plan

- **ML dropped.** Lean on emergent behavior, memory retrieval, LLM reasoning, and event
  sourcing. These are honest, hard, and demo well.
- **Theme: Cyberpunk Megacity.** Corporations, hackers, AI factions, crime syndicates.
  Better emergent stories than a generic city, still serious engineering.
- **Memory: tiered.** ChromaDB (vector memory) only for the ~5 LLM agents. The 95
  rule-based agents use a cheap structured event log — no embeddings needed.
- **Time Machine: event sourcing, not snapshots.** Store the immutable event stream;
  replay events to reconstruct any day. Cleaner, smaller, and a great interview topic.
- **Vertical slice first.** A tiny world that runs end-to-end early, then layer features.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  React Dashboard                              │
│  City grid · Relationship graph · Timeline    │
└───────────────┬───────────────────────────────┘
                │ REST + WebSocket
┌───────────────▼───────────────────────────────┐
│  FastAPI                                       │
│  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Sim Engine   │  │ Event Store (source   │   │
│  │ tick loop    │──│ of truth, append-only)│   │
│  └──────┬───────┘  └──────────┬────────────┘   │
│         │                     │                │
│  ┌──────▼──────┐  ┌───────────▼───────────┐    │
│  │ Agent brains│  │ Projections (read     │    │
│  │ T1 rules    │  │ models: state, graph, │    │
│  │ T2 LLM      │  │ news, timeline)       │    │
│  └──────┬──────┘  └───────────────────────┘    │
│         │                                      │
│  ┌──────▼──────┐  ┌──────────────────────┐     │
│  │ ChromaDB    │  │ PostgreSQL           │     │
│  │ (T2 memory) │  │ events + projections │     │
│  └─────────────┘  └──────────────────────┘     │
│         │                                      │
│  ┌──────▼──────┐                               │
│  │ Ollama      │  Qwen3 8B / DeepSeek 8B       │
│  └─────────────┘                               │
└────────────────────────────────────────────────┘
```

**Event sourcing is the backbone.** Every meaningful thing — an agent takes a job, two
agents meet, a corp opens a node — is an immutable event appended to the store. World
state, the relationship graph, news, and the timeline are all *projections* rebuilt from
events. The Time Machine is just "replay events up to day N."

---

## World

20x20 grid (400 tiles), 100 agents. Cyberpunk building types:

```
Hab-block (housing)   Corp tower (offices)
Market node (shops)   Net-cafe (school/training)
Enforcer post         Plaza (park)
```

Tick model: `1 tick = 1 hour`, `24 ticks = 1 day`. Daily cycle per agent:
morning → work → social → personal goal → sleep.

---

## Agents

```python
Agent:
    id, name, age, personality, occupation
    wealth, happiness, energy
    goals, relationships          # structured
    faction                        # corp / hacker / syndicate / unaligned
```

**Tier 1 — 95 agents, pure logic, no LLM.** Cheap rules: if unemployed → find_job;
if money < threshold → earn; if lonely → socialize. Runs every tick for everyone.

**Tier 2 — ~5 named agents (CEO, Hacker, Crime Boss, Influencer, Mayor/Arbiter).**
Call Ollama to generate *plans*, not per-tick actions (e.g. "open a second market node",
"start a turf move"). Plans decompose into events the engine executes over many ticks.
Keep LLM calls rare — planning beats per-tick reasoning for cost and coherence.

---

## Memory (tiered)

- **Tier 1:** append events to the structured log; query by recency/relevance with SQL.
- **Tier 2:** embed important events into ChromaDB. When an LLM agent plans, retrieve the
  top-k relevant memories ("Who helped me? Who undercut me?") and inject into the prompt.

```json
{ "agent": "Kade", "memory": "Vyn undercut my market node",
  "importance": 0.8, "day": 24 }
```

Importance scoring decides what gets embedded vs. logged, so Chroma stays small.

---

## Relationship engine

Per directed pair: `{ trust, friendship, rivalry }`. Events nudge values
(help → +trust/+friendship; betrayal → +rivalry/−trust). The relationship graph is a
projection: nodes = agents, green edges = friendship, red = rivalry, edge weight = strength.

---

## Emergent news

Each simulated day, summarize the day's high-importance events into headlines (template-
based to start; an LLM pass later if time allows). News is a projection over the event
stream, so it's consistent with the Time Machine.

---

## Time Machine (portfolio centerpiece)

Drag a timeline slider to any day; the UI replays the event stream up to that point and
renders city + graph + news for that moment. Because state is derived from events, replay
is exact and cheap — no snapshot storage, no drift.

---

## 8-week sequence (full-time)

**Week 1 — Foundation & vertical slice.** FastAPI + PostgreSQL, event store schema,
Agent model, tick loop. Goal: **10 agents living/working on a 10x10 grid, end-to-end,
events persisting.** This is the most important milestone — everything else layers on it.

**Week 2 — Sim engine & movement.** Full 20x20 grid, building types, pathfinding/movement,
Tier-1 rule behaviors, daily cycle. Scale to 100 agents.

**Week 3 — Relationship engine + projections.** Trust/friendship/rivalry, event-driven
updates, relationship-graph projection. Solidify the projection pattern.

**Week 4 — Memory + LLM agents.** ChromaDB for Tier-2, Ollama integration, planning loop,
memory retrieval into prompts. Get one named agent making coherent multi-day plans.

**Week 5 — React dashboard.** City grid render, agent inspector, live updates via
WebSocket. First time it *looks* alive.

**Week 6 — Relationship graph viz.** Force-directed graph (d3 / react-force-graph),
colored edges, evolves as you scrub time.

**Week 7 — News + Time Machine.** Daily headline generation, timeline slider, event replay
to any day. The wow feature.

**Week 8 — Polish & ship.** Seed an interesting scenario, record a demo GIF, write the
README (architecture diagram, the event-sourcing story, screenshots), deploy.

**Buffer reality check:** if anything slips, sacrifice Tier-2 LLM richness before the Time
Machine — the replay demo is what sells the project.

---

## Stack

FastAPI · PostgreSQL · ChromaDB · Ollama (Qwen3 8B / DeepSeek 8B) · React + WebSocket ·
d3/react-force-graph for the relationship graph.

## README talking points (for recruiters)

- Event-sourced simulation: append-only log as source of truth, everything else a projection.
- Tiered agent intelligence: 95 cheap rule agents + 5 LLM planners, mixed for cost/coherence.
- Vector memory retrieval driving LLM reasoning (RAG over an agent's own history).
- Deterministic time-travel replay built for free from the event model.
```

Then build it.