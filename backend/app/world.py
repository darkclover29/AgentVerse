"""Cyberpunk megacity grid generation."""
import json
import os
import random

from .config import GRID_SIZE, RANDOM_SEED

# Building types and their share of non-residential tiles.
BUILDING_TYPES = {
    "hab_block": "housing",
    "corp_tower": "office",
    "market_node": "shop",
    "net_cafe": "training",
    "enforcer_post": "security",
    "plaza": "leisure",
}

GRID_FILE = os.path.join(os.path.dirname(__file__), "grid.json")
_GRID = None


def generate_grid(seed: int = 42, size: int = GRID_SIZE):
    """Return a dict {(x, y): building_type} for the whole grid.

    Most tiles are hab_blocks; a scatter of corp towers, market nodes, etc. give the
    city its structure.
    """
    rng = random.Random(seed)
    grid = {}
    specials = [
        ("corp_tower", max(4, size * size // 40)),
        ("market_node", max(4, size * size // 30)),
        ("net_cafe", max(2, size * size // 80)),
        ("enforcer_post", max(2, size * size // 100)),
        ("plaza", max(3, size * size // 60)),
    ]
    coords = [(x, y) for x in range(size) for y in range(size)]
    rng.shuffle(coords)
    i = 0
    for btype, count in specials:
        for _ in range(count):
            if i >= len(coords):
                break
            grid[coords[i]] = btype
            i += 1
    for c in coords:
        grid.setdefault(c, "hab_block")
    return grid


def get_grid():
    global _GRID
    if _GRID is None:
        if os.path.exists(GRID_FILE):
            try:
                with open(GRID_FILE, "r") as f:
                    data = json.load(f)
                    _GRID = {tuple(map(int, k.split(","))): v for k, v in data.items()}
            except Exception:
                _GRID = generate_grid(seed=RANDOM_SEED, size=GRID_SIZE)
                save_grid()
        else:
            _GRID = generate_grid(seed=RANDOM_SEED, size=GRID_SIZE)
            save_grid()
    return _GRID


def save_grid():
    global _GRID
    if _GRID is not None:
        try:
            data = {f"{k[0]},{k[1]}": v for k, v in _GRID.items()}
            with open(GRID_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass


def update_tile(x: int, y: int, btype: str):
    global _GRID
    grid = get_grid()
    grid[(x, y)] = btype
    save_grid()


def tiles_of_type(grid, btype):
    return [xy for xy, t in grid.items() if t == btype]
