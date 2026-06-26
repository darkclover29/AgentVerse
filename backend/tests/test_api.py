"""API smoke tests via FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def _seed_module():
    # TestClient doesn't run the startup lifespan on bare calls, so seed explicitly.
    seed(reset=True)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_world_and_agents():
    assert client.get("/api/world").json()["grid_size"] == 20
    agents = client.get("/api/agents").json()
    assert len(agents) > 0


def test_agents_pagination_and_filter():
    page = client.get("/api/agents?limit=5").json()
    assert len(page) <= 5
    corp = client.get("/api/agents?faction=corp").json()
    assert all(a["faction"] == "corp" for a in corp)


def test_step_then_businesses_and_news():
    client.post("/api/reset")
    clock = client.post("/api/step", json={"ticks": 48}).json()
    assert clock["day"] == 2
    assert isinstance(client.get("/api/businesses").json(), list)
    assert "headlines" in client.get("/api/news?day=1").json()


def test_status_endpoint():
    body = client.get("/api/status").json()
    assert set(body) == {"ollama", "chroma", "model"}
