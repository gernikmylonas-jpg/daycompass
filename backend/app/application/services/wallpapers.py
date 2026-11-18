"""The nugget economy: every 10 points earned is one gold nugget; nuggets buy wallpapers.

Points are never reduced (they feed leaderboards and badges), so spending nuggets never touches them:
balance = floor(total_points / POINTS_PER_NUGGET) - the cost of everything already unlocked.
The unlocks table is the memory of what was spent and when.
"""
POINTS_PER_NUGGET = 10

# id, cost in nuggets, the compass style the picture belongs to (for display only)
CATALOG: list[dict] = [
    {"id": "topo", "cost": 5, "theme": "minimal"},
    {"id": "blueprint", "cost": 10, "theme": "modern"},
    {"id": "old_map", "cost": 10, "theme": "retro"},
    {"id": "ocean", "cost": 10, "theme": "nautical"},
    {"id": "dunes", "cost": 10, "theme": "explorer"},
    {"id": "mountains", "cost": 15, "theme": "classic"},
    {"id": "forest", "cost": 15, "theme": "explorer"},
    {"id": "gears", "cost": 15, "theme": "retro"},
    {"id": "night_sea", "cost": 20, "theme": "nautical"},
    {"id": "cyber_city", "cost": 20, "theme": "neon"},
    {"id": "aurora", "cost": 25, "theme": "classic"},
]
BY_ID = {w["id"]: w for w in CATALOG}
