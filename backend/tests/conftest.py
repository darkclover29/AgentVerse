"""Test fixtures. Env is set BEFORE importing the app so config picks it up:
a throwaway SQLite file, a small agent count for speed, and an unreachable Ollama URL
so the LLM planner deterministically uses its instant fallback."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_agentverse.db")
os.environ.setdefault("NUM_AGENTS", "40")
os.environ.setdefault("RANDOM_SEED", "7")
os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:9")  # refused fast → fallback

import pytest  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.seed import get_grid, seed  # noqa: E402


@pytest.fixture()
def db():
    seed(reset=True)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def grid():
    return get_grid()
