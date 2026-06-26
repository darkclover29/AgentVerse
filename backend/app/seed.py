"""Seed the world: build the grid, create agents, prime a few rivalries, reset the clock."""
import random

from .agents import generate_agents
from .config import GRID_SIZE, NUM_AGENTS, RANDOM_SEED
from .database import SessionLocal, init_db
from .models import Agent, Business, Event, Plan, Relationship, SimState
from .world import generate_grid, get_grid


def seed(reset: bool = True):
    if reset:
        from .database import engine, Base
        Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        # Self-healing: if the existing database has an outdated schema (e.g. missing columns),
        # query() will throw an OperationalError. In that case, force a reset to rebuild tables.
        try:
            db.query(Agent).count()
        except Exception:
            db.close()
            from .database import engine, Base
            Base.metadata.drop_all(bind=engine)
            init_db()
            db = SessionLocal()

        grid = get_grid()
        if db.query(Agent).count() == 0:
            for a in generate_agents(grid, seed=RANDOM_SEED, n=NUM_AGENTS):
                db.add(a)
            db.commit()
            _prime_rivalries(db)
        if db.get(SimState, 1) is None:
            db.add(SimState(id=1, day=0, tick=0))
        db.commit()
        return {"agents": db.query(Agent).count(), "grid_tiles": len(grid)}
    finally:
        db.close()


def _prime_rivalries(db, seed: int = RANDOM_SEED):
    """Seed a couple of cross-faction rivalries between Tier-2 agents so the opening
    days already have tension to escalate — better demo, more interesting news."""
    rng = random.Random(seed)
    leaders = db.query(Agent).filter(Agent.tier == 2).all()
    rng.shuffle(leaders)
    for i in range(0, len(leaders) - 1, 2):
        a, b = leaders[i], leaders[i + 1]
        for x, y in ((a.id, b.id), (b.id, a.id)):
            db.add(Relationship(a_id=x, b_id=y, trust=-20, friendship=0, rivalry=35))
    db.commit()


if __name__ == "__main__":
    print(seed())
