import os

# Load a .env file if python-dotenv is installed (optional; falls back to real env vars).
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# SQLite by default for zero-setup local dev. Swap to Postgres by setting DATABASE_URL,
# e.g. postgresql+psycopg://user:pass@localhost/agentverse
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentverse.db")

GRID_SIZE = int(os.getenv("GRID_SIZE", "20"))
NUM_AGENTS = int(os.getenv("NUM_AGENTS", "100"))
TICKS_PER_DAY = 24
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
