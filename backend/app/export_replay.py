import json
import os
from sqlalchemy.orm import Session

from .database import SessionLocal, init_db, engine, Base
from .seed import seed, get_grid
from .simulation import step_n
from .models import Agent, Relationship, Event, Business, Plan, SimState
from .newspaper import generate_newspaper

def run_and_export():
    print("Initializing and seeding database...")
    # Force drop and rebuild to ensure we start from clean Day 0
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    db = SessionLocal()
    try:
        # Run seed
        seed(reset=True)
        
        # Save initial world grid
        grid = get_grid()
        grid_tiles = [{"x": x, "y": y, "type": t} for (x, y), t in grid.items()]
        
        # Save initial agents
        initial_agents = []
        for a in db.query(Agent).all():
            initial_agents.append({
                "id": a.id,
                "name": a.name,
                "age": a.age,
                "gender": a.gender,
                "background": a.background,
                "personality": a.personality,
                "occupation": a.occupation,
                "faction": a.faction,
                "wealth": a.wealth,
                "happiness": a.happiness,
                "energy": a.energy,
                "x": a.x,
                "y": a.y,
                "tier": a.tier
            })
            
        # Save initial relationships
        initial_relationships = []
        for r in db.query(Relationship).all():
            initial_relationships.append({
                "a_id": r.a_id,
                "b_id": r.b_id,
                "trust": r.trust,
                "friendship": r.friendship,
                "rivalry": r.rivalry
            })
            
        print(f"Initial state captured. {len(initial_agents)} agents, {len(initial_relationships)} relationships.")
        
        # Run 30 days of simulation (30 * 24 = 720 ticks)
        print("Simulating 30 days of agent activity (using heuristic fallbacks)...")
        days = 30
        total_ticks = days * 24
        
        # Step the simulation
        step_n(db, grid, total_ticks)
        
        # Fetch all events
        print("Fetching events...")
        events = []
        for e in db.query(Event).order_by(Event.id.asc()).all():
            events.append({
                "id": e.id,
                "day": e.day,
                "tick": e.tick,
                "type": e.type,
                "agent_id": e.agent_id,
                "target_id": e.target_id,
                "payload": e.payload or {},
                "importance": e.importance
            })
            
        print(f"Total events captured: {len(events)}")
        
        # Generate newspapers for all 30 days
        print("Pre-rendering daily newspapers...")
        newspapers = {}
        for d in range(days + 1):
            try:
                newspapers[str(d)] = generate_newspaper(db, d)
            except Exception as ex:
                print(f"Error generating newspaper for day {d}: {ex}")
                
        # Fetch all plans
        print("Fetching plans...")
        plans = []
        for p in db.query(Plan).all():
            plans.append({
                "id": p.id,
                "agent_id": p.agent_id,
                "day_created": p.day_created,
                "goal": p.goal,
                "steps": p.steps or [],
                "step_index": p.step_index,
                "status": p.status,
                "source": p.source
            })
            
        # Compile everything into a single object
        replay_data = {
            "grid_size": 20,
            "grid_tiles": grid_tiles,
            "initial_agents": initial_agents,
            "initial_relationships": initial_relationships,
            "events": events,
            "newspapers": newspapers,
            "plans": plans
        }
        
        # Define output directory and file path (relative to repo root folder)
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "public")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        out_path = os.path.join(out_dir, "replay_data.json")
        print(f"Writing replay data to {out_path}...")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, indent=2, ensure_ascii=False)
            
        print("Replay data exported successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_and_export()
