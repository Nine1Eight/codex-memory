from __future__ import annotations

from dataclasses import dataclass

from collections import deque
from .map import Grid, dominant_color, grid_shape


def infer_walkability(grid, player=None):
    width, height = grid_shape(grid)
    if not width or not height:
        return frozenset(), frozenset(), {"kind": "empty", "regions": 0}
    background = dominant_color(grid)
    colors = {background}
    if player and 0 <= player[1] < height and 0 <= player[0] < width:
        colors.add(grid[player[1]][player[0]])
    free = frozenset((x, y) for y, row in enumerate(grid) for x, value in enumerate(row) if value in colors)
    blocked = frozenset((x, y) for y, row in enumerate(grid) for x, value in enumerate(row) if value not in colors)
    unseen = set(free); regions = 0
    while unseen:
        regions += 1; queue = deque([unseen.pop()])
        while queue:
            x, y = queue.popleft()
            for nxt in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if nxt in unseen: unseen.remove(nxt); queue.append(nxt)
    return free, blocked, {"kind":"grid","width":width,"height":height,"background":background,"free_count":len(free),"blocked_count":len(blocked),"regions":regions}


@dataclass(slots=True)
class Reachability:
    reachable: int
    blocked: int
    unknown: int


def summarize_topology(grid: Grid) -> dict[str, object]:
    if not grid:
        return {"kind": "empty", "reachability": Reachability(0, 0, 0).__dict__}
    colors = {}
    for row in grid:
        for cell in row:
            colors[cell] = colors.get(cell, 0) + 1
    return {"kind": "grid", "colors": colors}
