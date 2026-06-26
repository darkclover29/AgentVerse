"""Tests for the daily newspaper generator endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed import seed

client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def _seed_module():
    seed(reset=True)

def test_newspaper_structure_and_fallback():
    # Reset and step so we have events on Day 1
    client.post("/api/reset")
    clock = client.post("/api/step", json={"ticks": 24}).json()
    assert clock["day"] == 1

    # Request the newspaper for Day 1
    r = client.get("/api/newspaper?day=1")
    assert r.status_code == 200
    
    data = r.json()
    assert data["day"] == 1
    assert "edition" in data
    assert "date" in data
    assert "weather" in data
    assert "pages" in data

    weather = data["weather"]
    assert "acid_rain" in weather
    assert "smog_density" in weather
    assert "grid_latency" in weather
    assert "advisory" in weather

    pages = data["pages"]
    assert len(pages) == 3

    # Check Page 1: Front Page
    front_page = pages[0]
    assert front_page["id"] == "front"
    assert front_page["title"] == "Front Page"
    assert "articles" in front_page
    assert "bulletins" in front_page
    assert len(front_page["articles"]) > 0
    assert front_page["articles"][0]["type"] == "headline"
    assert "title" in front_page["articles"][0]
    assert "body" in front_page["articles"][0]
    assert "author" in front_page["articles"][0]

    # Check Page 2: Metapolitics
    factions_page = pages[1]
    assert factions_page["id"] == "factions"
    assert factions_page["title"] == "Metapolitics"
    assert "articles" in factions_page
    assert "ads" in factions_page
    assert len(factions_page["articles"]) > 0
    assert factions_page["articles"][0]["type"] == "faction"
    assert len(factions_page["ads"]) == 3

    # Check Page 3: Local Scandals
    scandals_page = pages[2]
    assert scandals_page["id"] == "scandals"
    assert scandals_page["title"] == "Local Scandals"
    assert "articles" in scandals_page
    assert "gossip" in scandals_page
    assert len(scandals_page["articles"]) > 0
    assert scandals_page["articles"][0]["type"] == "opinion"
