"""Projections derived from the event stream."""
from app import simulation
from app.models import Agent


def test_graph_and_news_after_running(db, grid):
    simulation.step_n(db, grid, 24 * 3)
    from app import projections
    g = projections.relationship_graph(db)
    assert len(g["nodes"]) == db.query(Agent).count()
    assert isinstance(g["edges"], list)
    news = projections.daily_news(db, 1)
    assert "headlines" in news


def test_replay_reconstructs_all_agents(db, grid):
    simulation.step_n(db, grid, 24 * 2)
    from app import projections
    snap = projections.replay_to_day(db, 1)
    assert len(snap["agents"]) == db.query(Agent).count()


def test_history_returns_series(db, grid):
    simulation.step_n(db, grid, 24 * 2)
    from app import projections
    a = db.query(Agent).first()
    hist = projections.agent_history(db, a.id)
    assert hist["agent_id"] == a.id
    assert isinstance(hist["series"], list)
