"""Deterministic environmental rules for Monsoon, AQI, and Traffic congestion."""
from .world import get_grid

def is_monsoon(day: int, tick: int) -> bool:
    # Monsoon active on day 2 and 3 of every 5-day cycle
    return (day % 5) in (2, 3)

def get_flooded_tiles(day: int, tick: int) -> list[tuple[int, int]]:
    if not is_monsoon(day, tick):
        return []
    
    grid = get_grid()
    flooded = [coord for coord, btype in grid.items() if btype == "plaza"]
    
    # Deterministic waterlogged spots on y=5,6,7 rows
    for y in (5, 6, 7):
        for x in range(20):
            if (x + y + day) % 4 == 0:
                flooded.append((x, y))
                
    return sorted(list(set(flooded)))

def is_flooded(x: int, y: int, day: int, tick: int) -> bool:
    if not is_monsoon(day, tick):
        return False
    grid = get_grid()
    if grid.get((x, y)) == "plaza":
        return True
    if y in (5, 6, 7) and (x + y + day) % 4 == 0:
        return True
    return False

def get_aqi(day: int, tick: int) -> int:
    # AQI varies from 50 to 450, peaking during daily work hours
    base = 100 + (day * 8) % 150
    if 7 <= tick <= 18:
        # Triangular peak shape around tick 12-13
        peak_adder = (tick - 7) * 25 if tick < 13 else (18 - tick) * 25
        base += peak_adder
    return int(base)

def get_aqi_status(aqi: int) -> str:
    if aqi < 100:
        return "GOOD"
    elif aqi < 200:
        return "MODERATE"
    elif aqi < 300:
        return "POOR"
    elif aqi < 400:
        return "VERY POOR"
    return "SEVERE"

def is_traffic_gridlock_active(day: int, tick: int) -> bool:
    return (7 <= tick <= 9) or (16 <= tick <= 18)

def get_gridlock_tiles(day: int, tick: int) -> list[tuple[int, int]]:
    if not is_traffic_gridlock_active(day, tick):
        return []
    return [(x, 10) for x in range(20)]

def is_traffic_gridlock(x: int, y: int, day: int, tick: int) -> bool:
    return y == 10 and is_traffic_gridlock_active(day, tick)

def get_environment_state(day: int, tick: int) -> dict:
    aqi = get_aqi(day, tick)
    return {
        "day": day,
        "tick": tick,
        "is_monsoon": is_monsoon(day, tick),
        "flooded_tiles": [list(t) for t in get_flooded_tiles(day, tick)],
        "aqi_level": aqi,
        "aqi_status": get_aqi_status(aqi),
        "is_traffic_gridlock": is_traffic_gridlock_active(day, tick),
        "gridlock_tiles": [list(t) for t in get_gridlock_tiles(day, tick)]
    }
