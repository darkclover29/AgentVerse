"""Tests for the timeline and direct chat communication features."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def _seed_module():
    # TestClient doesn't run the startup lifespan on bare calls, so seed explicitly.
    seed(reset=True)


def test_timeline_endpoint():
    # 1. Fetch agents to get a valid agent_id
    agents = client.get("/api/agents").json()
    assert len(agents) > 0
    agent_id = agents[0]["id"]
    
    # 2. Query timeline
    r = client.get(f"/api/agents/{agent_id}/timeline")
    assert r.status_code == 200
    timeline = r.json()
    assert isinstance(timeline, list)


def test_chat_endpoint_procedural_fallback():
    # 1. Fetch agents to get a valid agent_id
    agents = client.get("/api/agents").json()
    assert len(agents) > 0
    agent = agents[0]
    agent_id = agent["id"]
    
    # 2. Send plan request
    r = client.post(
        f"/api/agents/{agent_id}/chat",
        json={"message": "What is your plan?", "history": []}
    )
    assert r.status_code == 200
    reply = r.json()
    assert "text" in reply
    assert isinstance(reply["text"], str)
    assert len(reply["text"]) > 0

    # 3. Send money request
    r = client.post(
        f"/api/agents/{agent_id}/chat",
        json={"message": "How much money do you have?", "history": []}
    )
    assert r.status_code == 200
    reply = r.json()
    assert "text" in reply
    reply_text = reply["text"].lower()
    assert "₹" in reply["text"] or "capital" in reply_text or "savings" in reply_text or "fees" in reply_text or "budget" in reply_text

    # 4. Send faction request
    r = client.post(
        f"/api/agents/{agent_id}/chat",
        json={"message": "What do you think of your faction?", "history": []}
    )
    assert r.status_code == 200
    reply = r.json()
    assert "text" in reply

    # 5. Send general query with history
    history = [
        {"sender": "user", "text": "Hello there"},
        {"sender": "agent", "text": "Who is this?"}
    ]
    r = client.post(
        f"/api/agents/{agent_id}/chat",
        json={"message": "I am the Observer.", "history": history}
    )
    assert r.status_code == 200
    reply = r.json()
    assert "text" in reply


def test_agent_gender_and_background():
    # 1. Fetch all agents
    r = client.get("/api/agents")
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) > 0
    
    # 2. Assert gender and background are present and valid
    for agent in agents:
        assert "gender" in agent
        assert agent["gender"] in ["Male", "Female", "Non-binary"]
        assert "background" in agent
        assert isinstance(agent["background"], str)
        assert len(agent["background"]) > 0

