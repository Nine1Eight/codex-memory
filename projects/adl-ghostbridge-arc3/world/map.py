from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Iterable


Grid = list[list[int]]


def dominant_color(grid):
    counts = Counter(cell for row in grid for cell in row)
    return counts.most_common(1)[0][0] if counts else None


@dataclass(slots=True)
class ConnectedComponent:
    color: int
    cells: list[tuple[int, int]]

    @property
    def centroid(self) -> tuple[float, float]:
        xs = [x for x, _ in self.cells]
        ys = [y for _, y in self.cells]
        return (sum(xs) / len(xs), sum(ys) / len(ys))


def normalize_grid(frame: Iterable[Iterable[int]]) -> Grid:
    grid = [list(row) for row in frame]
    if not grid:
        return []
    width = max(len(row) for row in grid)
    return [row + [0] * (width - len(row)) for row in grid]


def grid_shape(grid: Grid) -> tuple[int, int]:
    if not grid:
        return (0, 0)
    return (len(grid[0]), len(grid))


def connected_components(grid: Grid, include_background: bool = False) -> list[ConnectedComponent]:
    if not grid:
        return []
    width, height = grid_shape(grid)
    seen: set[tuple[int, int]] = set()
    out: list[ConnectedComponent] = []
    background = dominant_color(grid)
    for y in range(height):
        for x in range(width):
            if (x, y) in seen:
                continue
            color = grid[y][x]
            q = deque([(x, y)])
            seen.add((x, y))
            cells: list[tuple[int, int]] = []
            while q:
                cx, cy = q.popleft()
                if grid[cy][cx] != color:
                    continue
                cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and grid[ny][nx] == color:
                        seen.add((nx, ny))
                        q.append((nx, ny))
            if include_background or color != background:
                out.append(ConnectedComponent(color=color, cells=cells))
    return out
