# AgentVerse — Demo Walkthrough

A 3-minute script for showing the project (recruiter demo or a recorded GIF).

## Setup (once)

1. Run `start.bat` (or start backend + frontend manually — see README).
2. Optional but recommended: `ollama pull qwen3:8b` so the 5 Tier-2 agents plan with a
   real LLM. Without it they use the heuristic planner and everything still works.
3. Open http://localhost:5173.

## The script

**1. The living city (~30s).**
Press **▶ Run**. Point out the 100 agents commuting across the 20×20 grid — colored by
faction (corp/hacker/syndicate/unaligned), the 5 amber-ringed dots are the LLM planners.
The HUD ticks through day/time and shows live firm count and total wealth.

**2. Emergent economy (~40s).**
Let it run a few days. Amber diamonds appear as agents found businesses; watch the **City
Feed** for headlines — "X opened Neon Market Node", "Y hired Z", and eventually
"…went under — ruined" as over-competed markets collapse. This is unscripted: it falls out
of the simulation rules.

**3. Inside an agent's head (~40s).**
Click a ★ LLM agent. The panel shows its **wealth/happiness sparklines**, its current
**goal and plan** (with completed steps struck through), the **memories** it retrieved to
make that plan, and its **relationships** (♥ allies / ⚔ rivals). This is the
RAG-grounded reasoning loop made visible.

**4. The relationship network (~30s).**
Switch to the **Network** tab and hit **⟳ Refresh**. A force-directed graph of all 100
agents — green friendship edges, red rivalry edges, node size = number of connections.
Hover a node to isolate its connections. The primed rivalries have escalated into clusters.

**5. The Time Machine (~20s).**
Back on **City**, drag the timeline slider. The whole world — agent positions, wealth,
news — reconstructs to any past day by replaying the event stream. Nothing is snapshotted;
state is a pure fold over events. This is the headline architecture point.

## One-liner for the résumé

> Event-sourced multi-agent simulation: 95 rule-based + 5 LLM-planning agents with vector
> memory, an emergent business economy, a force-directed relationship graph, and
> deterministic time-travel replay — FastAPI + React.
