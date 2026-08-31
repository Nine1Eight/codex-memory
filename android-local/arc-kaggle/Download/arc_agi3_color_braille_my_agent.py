"""
agent/my_agent.py

Nine1Eight Braille-Sigil ARC-AGI-3 agent.

Drop-in target
--------------
Place this file at:
    ARC-AGI-3-Kaggle-Starter/agent/my_agent.py

It implements the current ARC-AGI-3 starter contract:
    class MyAgent(Agent):
        def is_done(self, frames, latest_frame) -> bool
        def choose_action(self, frames, latest_frame) -> GameAction

Core idea
---------
Every observed game frame is reduced into a 64x64 binary occupancy map, then
packed into Unicode Braille using the ISO 11548-1 / drawille-style 2x4 dot cell
layout. That gives a compact, deterministic visual state signature:

    raw frame -> background-separated occupancy -> 64x64 -> 32x16 Braille -> hash/stats

The policy layer uses that signature to build a small online world model:
state-action transitions, novelty, progress, no-op penalties, and salience-based
click targets. No API calls, no external models, no hard-coded private game
solutions, and no dependency beyond the ARC starter runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# ARC runtime imports with safe local-test fallbacks.
# In the official ARC-AGI-3 runtime these imports resolve to the real classes.
# ---------------------------------------------------------------------------
try:  # ARC-AGI-3-Agents / current starter path
    from arcengine import FrameData, GameAction, GameState  # type: ignore
except Exception:  # pragma: no cover - fallback exists for local lint/smoke tests
    class GameState(Enum):
        NOT_PLAYED = "NOT_PLAYED"
        PLAYING = "PLAYING"
        WIN = "WIN"
        GAME_OVER = "GAME_OVER"

    class _FallbackActionData:
        def __init__(self) -> None:
            self.data: Dict[str, Any] = {}

        def model_dump(self) -> Dict[str, Any]:
            return dict(self.data)

    class GameAction(Enum):
        RESET = 0
        ACTION1 = 1
        ACTION2 = 2
        ACTION3 = 3
        ACTION4 = 4
        ACTION5 = 5
        ACTION6 = 6
        ACTION7 = 7

        def is_simple(self) -> bool:
            return self is not GameAction.ACTION6

        def is_complex(self) -> bool:
            return self is GameAction.ACTION6

        def set_data(self, data: Dict[str, Any]) -> None:
            self.action_data = _FallbackActionData()
            self.action_data.data.update(data)

        @classmethod
        def from_id(cls, value: int) -> "GameAction":
            for action in cls:
                if int(action.value) == int(value):
                    return action
            raise ValueError(f"unknown fallback action id: {value}")

    @dataclass
    class FrameData:  # type: ignore
        frame: Any = None
        state: Any = GameState.PLAYING
        levels_completed: int = 0
        win_levels: int = 1
        available_actions: Any = None
        guid: str = ""
        game_id: str = "local"

try:
    from .agent import Agent  # type: ignore
except Exception:
    try:
        from agents.agent import Agent  # type: ignore
    except Exception:  # pragma: no cover - fallback for isolated import tests
        class Agent:  # type: ignore
            MAX_ACTIONS = 80

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.action_counter = 0
                self.game_id = kwargs.get("game_id", "local")


# ---------------------------------------------------------------------------
# Braille/ISO 11548-1 occupancy grid.
# ---------------------------------------------------------------------------
GRID_W = 64
GRID_H = 64
CELL_W = 2
CELL_H = 4
GLYPH_COLS = GRID_W // CELL_W
GLYPH_ROWS = GRID_H // CELL_H
BRAILLE_BASE = 0x2800

# (local_x, local_y) -> bit index, standard 8-dot Braille cell ordering.
_DOT_BIT: Dict[Tuple[int, int], int] = {
    (0, 0): 0,  # dot 1
    (0, 1): 1,  # dot 2
    (0, 2): 2,  # dot 3
    (1, 0): 3,  # dot 4
    (1, 1): 4,  # dot 5
    (1, 2): 5,  # dot 6
    (0, 3): 6,  # dot 7
    (1, 3): 7,  # dot 8
}


class BrailleGrid64:
    """64x64 binary occupancy grid with Unicode Braille rendering."""

    __slots__ = ("_cells",)

    def __init__(self) -> None:
        self._cells = bytearray(GRID_W * GRID_H)

    @classmethod
    def from_points(cls, points: Iterable[Tuple[int, int]]) -> "BrailleGrid64":
        grid = cls()
        for x, y in points:
            grid.set(x, y, True)
        return grid

    @classmethod
    def from_matrix(cls, matrix: Sequence[Sequence[int]]) -> "BrailleGrid64":
        if len(matrix) != GRID_H:
            raise ValueError(f"matrix must have {GRID_H} rows, got {len(matrix)}")
        grid = cls()
        for y, row in enumerate(matrix):
            if len(row) != GRID_W:
                raise ValueError(f"row {y} must have {GRID_W} columns, got {len(row)}")
            for x, value in enumerate(row):
                if value:
                    grid.set(x, y, True)
        return grid

    def _check_bounds(self, x: int, y: int) -> None:
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            raise IndexError(f"point ({x}, {y}) out of bounds for {GRID_W}x{GRID_H} grid")

    def set(self, x: int, y: int, val: bool = True) -> None:
        self._check_bounds(x, y)
        self._cells[y * GRID_W + x] = 1 if val else 0

    def get(self, x: int, y: int) -> bool:
        self._check_bounds(x, y)
        return bool(self._cells[y * GRID_W + x])

    def clear(self) -> None:
        self._cells = bytearray(GRID_W * GRID_H)

    def points(self) -> List[Tuple[int, int]]:
        return [
            (x, y)
            for y in range(GRID_H)
            for x in range(GRID_W)
            if self._cells[y * GRID_W + x]
        ]

    def to_cell_bytes(self) -> List[List[int]]:
        out = [[0] * GLYPH_COLS for _ in range(GLYPH_ROWS)]
        for gy in range(GLYPH_ROWS):
            base_y = gy * CELL_H
            for gx in range(GLYPH_COLS):
                base_x = gx * CELL_W
                byte_value = 0
                for (local_x, local_y), bit in _DOT_BIT.items():
                    index = (base_y + local_y) * GRID_W + (base_x + local_x)
                    if self._cells[index]:
                        byte_value |= 1 << bit
                out[gy][gx] = byte_value
        return out

    def to_braille_lines(self) -> List[str]:
        return [
            "".join(chr(BRAILLE_BASE + byte_value) for byte_value in row)
            for row in self.to_cell_bytes()
        ]

    def to_braille_string(self) -> str:
        return "\n".join(self.to_braille_lines())

    def _bounding_box(self) -> Optional[Tuple[int, int, int, int]]:
        pts = self.points()
        if not pts:
            return None
        xs = [point[0] for point in pts]
        ys = [point[1] for point in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def _centroid(self) -> Optional[Tuple[float, float]]:
        pts = self.points()
        if not pts:
            return None
        return (
            sum(point[0] for point in pts) / len(pts),
            sum(point[1] for point in pts) / len(pts),
        )

    def _connected_components(self, connectivity: int = 8) -> List[List[Tuple[int, int]]]:
        if connectivity not in (4, 8):
            raise ValueError("connectivity must be 4 or 8")

        if connectivity == 4:
            neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        else:
            neighbors = [
                (-1, -1), (0, -1), (1, -1),
                (-1, 0),           (1, 0),
                (-1, 1),  (0, 1),  (1, 1),
            ]

        seen = bytearray(GRID_W * GRID_H)
        components: List[List[Tuple[int, int]]] = []

        for y in range(GRID_H):
            for x in range(GRID_W):
                index = y * GRID_W + x
                if not self._cells[index] or seen[index]:
                    continue

                component: List[Tuple[int, int]] = []
                queue = deque([(x, y)])
                seen[index] = 1

                while queue:
                    current_x, current_y = queue.popleft()
                    component.append((current_x, current_y))
                    for dx, dy in neighbors:
                        nx = current_x + dx
                        ny = current_y + dy
                        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                            neighbor_index = ny * GRID_W + nx
                            if self._cells[neighbor_index] and not seen[neighbor_index]:
                                seen[neighbor_index] = 1
                                queue.append((nx, ny))

                components.append(component)

        return components

    def _symmetry(self, bbox: Optional[Tuple[int, int, int, int]]) -> Tuple[bool, bool]:
        if bbox is None:
            return False, False
        x0, y0, x1, y1 = bbox
        pts = set(self.points())
        horizontal_mirror = all((x0 + x1 - x, y) in pts for x, y in pts)
        vertical_mirror = all((x, y0 + y1 - y) in pts for x, y in pts)
        return horizontal_mirror, vertical_mirror

    def _quadrant_density(self) -> Dict[str, Dict[str, float | int]]:
        midx = GRID_W // 2
        midy = GRID_H // 2
        counts = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
        for x, y in self.points():
            vertical = "N" if y < midy else "S"
            horizontal = "W" if x < midx else "E"
            counts[vertical + horizontal] += 1
        areas = {
            "NW": midx * midy,
            "NE": (GRID_W - midx) * midy,
            "SW": midx * (GRID_H - midy),
            "SE": (GRID_W - midx) * (GRID_H - midy),
        }
        return {
            quadrant: {
                "points": counts[quadrant],
                "density": round(counts[quadrant] / areas[quadrant], 6) if areas[quadrant] else 0.0,
            }
            for quadrant in ("NW", "NE", "SW", "SE")
        }

    def describe(self) -> Dict[str, Any]:
        pts = self.points()
        bbox = self._bounding_box()
        centroid = self._centroid()
        components_4 = self._connected_components(4)
        components_8 = self._connected_components(8)
        horizontal_mirror, vertical_mirror = self._symmetry(bbox)
        if bbox is None:
            bbox_info = None
        else:
            bbox_info = {
                "x_min": bbox[0],
                "y_min": bbox[1],
                "x_max": bbox[2],
                "y_max": bbox[3],
                "width": bbox[2] - bbox[0] + 1,
                "height": bbox[3] - bbox[1] + 1,
            }
        return {
            "grid_size": [GRID_W, GRID_H],
            "point_count": len(pts),
            "density_overall": round(len(pts) / (GRID_W * GRID_H), 6),
            "bounding_box": bbox_info,
            "centroid": {"x": round(centroid[0], 3), "y": round(centroid[1], 3)} if centroid else None,
            "connected_components_4conn": len(components_4),
            "connected_components_8conn": len(components_8),
            "largest_component_size": max((len(component) for component in components_8), default=0),
            "symmetry": {
                "horizontal_mirror": horizontal_mirror,
                "vertical_mirror": vertical_mirror,
            },
            "quadrant_density": self._quadrant_density(),
        }


@dataclass
class BrailleGridAgent:
    grid: BrailleGrid64 = field(default_factory=BrailleGrid64)

    def load_points(self, points: Iterable[Tuple[int, int]], reset: bool = True) -> "BrailleGridAgent":
        if reset:
            self.grid.clear()
        for x, y in points:
            self.grid.set(x, y, True)
        return self

    def load_matrix(self, matrix: Sequence[Sequence[int]]) -> "BrailleGridAgent":
        self.grid = BrailleGrid64.from_matrix(matrix)
        return self

    def describe_json(self) -> Dict[str, Any]:
        out = self.grid.describe()
        out["braille"] = self.grid.to_braille_lines()
        return out


COLOR_NAMES: Dict[int, str] = {
    0: "black/empty",
    1: "blue",
    2: "red",
    3: "green",
    4: "yellow",
    5: "gray",
    6: "magenta",
    7: "orange",
    8: "cyan",
    9: "pink",
}


def _validate_color(value: int) -> int:
    ivalue = int(value)
    if not 0 <= ivalue <= 9:
        raise ValueError(f"ARC color must be in 0..9, got {value!r}")
    return ivalue


def _bbox(points: Sequence[Tuple[int, int]]) -> Optional[Dict[str, int]]:
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys),
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
    }


def _centroid(points: Sequence[Tuple[int, int]]) -> Optional[Dict[str, float]]:
    if not points:
        return None
    return {
        "x": round(sum(x for x, _ in points) / len(points), 3),
        "y": round(sum(y for _, y in points) / len(points), 3),
    }


class ARCGrid:
    """Multi-color ARC grid backed by a 64x64 bytearray.

    `width` and `height` retain the logical task/frame size. Storage remains fixed
    at 64x64 so Braille rendering is deterministic and no padding branch is needed.
    """

    __slots__ = ("_cells", "width", "height")

    def __init__(self, width: int = GRID_W, height: int = GRID_H) -> None:
        if not (1 <= int(width) <= GRID_W and 1 <= int(height) <= GRID_H):
            raise ValueError(f"ARCGrid logical size must fit within {GRID_W}x{GRID_H}, got {width}x{height}")
        self.width = int(width)
        self.height = int(height)
        self._cells = bytearray(GRID_W * GRID_H)

    @classmethod
    def from_matrix(cls, matrix: Sequence[Sequence[int]]) -> "ARCGrid":
        if not matrix:
            return cls(1, 1)
        height = len(matrix)
        width = max((len(row) for row in matrix), default=0)
        if width <= 0:
            return cls(1, 1)
        if width > GRID_W or height > GRID_H:
            matrix = cls._resample_matrix(matrix, GRID_W, GRID_H)
            height, width = GRID_H, GRID_W
        grid = cls(width, height)
        for y, row in enumerate(matrix):
            for x in range(width):
                value = row[x] if x < len(row) else 0
                grid.set(x, y, _validate_color(value))
        return grid

    @staticmethod
    def _resample_matrix(matrix: Sequence[Sequence[int]], target_w: int, target_h: int) -> List[List[int]]:
        src_h = len(matrix)
        src_w = max((len(row) for row in matrix), default=1)
        out: List[List[int]] = []
        for ty in range(target_h):
            sy = min(src_h - 1, max(0, int((ty + 0.5) * src_h / target_h)))
            row_out: List[int] = []
            row = matrix[sy] if sy < len(matrix) else []
            for tx in range(target_w):
                sx = min(src_w - 1, max(0, int((tx + 0.5) * src_w / target_w)))
                row_out.append(_validate_color(row[sx] if sx < len(row) else 0))
            out.append(row_out)
        return out

    def clone(self) -> "ARCGrid":
        copied = ARCGrid(self.width, self.height)
        copied._cells[:] = self._cells
        return copied

    def set(self, x: int, y: int, value: int) -> None:
        if not (0 <= int(x) < self.width and 0 <= int(y) < self.height):
            raise IndexError(f"point ({x}, {y}) out of bounds for {self.width}x{self.height}")
        self._cells[int(y) * GRID_W + int(x)] = _validate_color(value)

    def get(self, x: int, y: int) -> int:
        if not (0 <= int(x) < self.width and 0 <= int(y) < self.height):
            return 0
        return int(self._cells[int(y) * GRID_W + int(x)])

    def to_matrix(self) -> List[List[int]]:
        return [[self.get(x, y) for x in range(self.width)] for y in range(self.height)]

    def points(self, include_zero: bool = False) -> List[Tuple[int, int, int]]:
        pts: List[Tuple[int, int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                color = self.get(x, y)
                if include_zero or color != 0:
                    pts.append((x, y, color))
        return pts

    def occupied_points(self) -> List[Tuple[int, int]]:
        return [(x, y) for x, y, color in self.points(False) if color != 0]

    def color_histogram(self) -> Dict[int, int]:
        counts: Dict[int, int] = {color: 0 for color in range(10)}
        for _, _, color in self.points(include_zero=True):
            counts[color] += 1
        return {color: count for color, count in counts.items() if count > 0}

    def to_braille_lines(self) -> List[str]:
        out = [[0] * GLYPH_COLS for _ in range(GLYPH_ROWS)]
        for gy in range(GLYPH_ROWS):
            base_y = gy * CELL_H
            for gx in range(GLYPH_COLS):
                base_x = gx * CELL_W
                byte_value = 0
                for (lx, ly), bit in _DOT_BIT.items():
                    if self.get(base_x + lx, base_y + ly) != 0:
                        byte_value |= 1 << bit
                out[gy][gx] = byte_value
        return ["".join(chr(BRAILLE_BASE + value) for value in row) for row in out]

    def to_braille_string(self) -> str:
        return "\n".join(self.to_braille_lines())

    def render_colored_legend(self) -> str:
        present = self.color_histogram()
        return "Colors: " + ", ".join(f"{color}:{COLOR_NAMES[color]}" for color in sorted(present) if color != 0)

    def render_full(self) -> str:
        return "```\n" + self.to_braille_string() + "\n```\n" + self.render_colored_legend()

    def connected_components(self, color: Optional[int] = None, connectivity: int = 8) -> List[List[Tuple[int, int]]]:
        if connectivity not in (4, 8):
            raise ValueError("connectivity must be 4 or 8")
        if color is not None:
            color = _validate_color(color)
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if connectivity == 8:
            neighbors = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        seen = bytearray(GRID_W * GRID_H)
        components: List[List[Tuple[int, int]]] = []
        for y in range(self.height):
            for x in range(self.width):
                current = self.get(x, y)
                if current == 0 or seen[y * GRID_W + x] or (color is not None and current != color):
                    continue
                comp: List[Tuple[int, int]] = []
                q: deque[Tuple[int, int]] = deque([(x, y)])
                seen[y * GRID_W + x] = 1
                while q:
                    cx, cy = q.popleft()
                    comp.append((cx, cy))
                    for dx, dy in neighbors:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            idx = ny * GRID_W + nx
                            if not seen[idx] and self.get(nx, ny) == current:
                                seen[idx] = 1
                                q.append((nx, ny))
                components.append(comp)
        return components

    def objects_by_color(self, connectivity: int = 8) -> Dict[int, List[List[Tuple[int, int]]]]:
        result: DefaultDict[int, List[List[Tuple[int, int]]]] = defaultdict(list)
        for comp in self.connected_components(None, connectivity):
            if comp:
                result[self.get(comp[0][0], comp[0][1])].append(comp)
        return dict(result)

    def color_bounding_boxes(self) -> Dict[int, Optional[Dict[str, int]]]:
        boxes: Dict[int, Optional[Dict[str, int]]] = {}
        for color in sorted(self.objects_by_color().keys()):
            color_points = [(x, y) for x, y, c in self.points(False) if c == color]
            boxes[color] = _bbox(color_points)
        return boxes

    def quadrant_density(self) -> Dict[str, Dict[str, float | int]]:
        midx = max(1, self.width // 2)
        midy = max(1, self.height // 2)
        counts = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
        areas = {
            "NW": midx * midy,
            "NE": (self.width - midx) * midy,
            "SW": midx * (self.height - midy),
            "SE": (self.width - midx) * (self.height - midy),
        }
        for x, y in self.occupied_points():
            key = ("N" if y < midy else "S") + ("W" if x < midx else "E")
            counts[key] += 1
        return {q: {"points": counts[q], "density": round(counts[q] / areas[q], 6) if areas[q] else 0.0} for q in counts}

    def symmetry(self) -> Dict[str, bool]:
        pts_by_color = {(x, y): color for x, y, color in self.points(False)}
        occupied = [(x, y) for x, y, _ in self.points(False)]
        box = _bbox(occupied)
        if box is None:
            return {"horizontal_mirror": False, "vertical_mirror": False, "main_diagonal": False, "anti_diagonal": False}
        x0, x1 = box["x_min"], box["x_max"]
        y0, y1 = box["y_min"], box["y_max"]
        horizontal = all(pts_by_color.get((x0 + x1 - x, y)) == color for (x, y), color in pts_by_color.items())
        vertical = all(pts_by_color.get((x, y0 + y1 - y)) == color for (x, y), color in pts_by_color.items())
        main_diag = box["width"] == box["height"] and all(
            pts_by_color.get((x0 + (y - y0), y0 + (x - x0))) == color for (x, y), color in pts_by_color.items()
        )
        anti_diag = box["width"] == box["height"] and all(
            pts_by_color.get((x0 + (y1 - y), y0 + (x1 - x))) == color for (x, y), color in pts_by_color.items()
        )
        return {"horizontal_mirror": horizontal, "vertical_mirror": vertical, "main_diagonal": main_diag, "anti_diagonal": anti_diag}

    def crop_to_bbox(self, bbox: Optional[Dict[str, int]] = None) -> "ARCGrid":
        bbox = bbox or _bbox(self.occupied_points())
        if bbox is None:
            return ARCGrid(1, 1)
        matrix = [
            [self.get(x, y) for x in range(bbox["x_min"], bbox["x_max"] + 1)]
            for y in range(bbox["y_min"], bbox["y_max"] + 1)
        ]
        return ARCGrid.from_matrix(matrix)

    def rotate90(self, turns: int = 1) -> "ARCGrid":
        turns = turns % 4
        matrix = self.to_matrix()
        for _ in range(turns):
            matrix = [list(row) for row in zip(*matrix[::-1])]
        return ARCGrid.from_matrix(matrix)

    def flip_horizontal(self) -> "ARCGrid":
        return ARCGrid.from_matrix([list(reversed(row)) for row in self.to_matrix()])

    def flip_vertical(self) -> "ARCGrid":
        return ARCGrid.from_matrix(list(reversed(self.to_matrix())))

    def translate(self, dx: int, dy: int, background: int = 0) -> "ARCGrid":
        out = ARCGrid(self.width, self.height)
        for y in range(self.height):
            for x in range(self.width):
                out.set(x, y, background)
        for x, y, color in self.points(False):
            nx, ny = x + int(dx), y + int(dy)
            if 0 <= nx < self.width and 0 <= ny < self.height:
                out.set(nx, ny, color)
        return out

    def describe(self) -> Dict[str, Any]:
        objects = self.objects_by_color(connectivity=8)
        occupied = self.occupied_points()
        object_summaries: Dict[int, List[Dict[str, Any]]] = {}
        for color, comps in sorted(objects.items()):
            object_summaries[color] = [
                {
                    "size": len(comp),
                    "bbox": _bbox(comp),
                    "centroid": _centroid(comp),
                }
                for comp in comps
            ]
        return {
            "grid_size": [self.width, self.height],
            "total_colored_cells": len(occupied),
            "density_overall": round(len(occupied) / max(1, self.width * self.height), 6),
            "colors_present": sorted(objects.keys()),
            "color_histogram": self.color_histogram(),
            "objects_per_color": {color: len(comps) for color, comps in sorted(objects.items())},
            "largest_object_size": max((len(comp) for comps in objects.values() for comp in comps), default=0),
            "bounding_box": _bbox(occupied),
            "centroid": _centroid(occupied),
            "color_bounding_boxes": self.color_bounding_boxes(),
            "quadrant_density": self.quadrant_density(),
            "symmetry": self.symmetry(),
            "objects": object_summaries,
            "braille": self.to_braille_lines(),
        }


@dataclass
class ARCGridAgent:
    """Stateful wrapper for ARC task, train/test pair, or single matrix analysis."""

    grid: ARCGrid = field(default_factory=ARCGrid)

    def load_task_pair(self, pair: Dict[str, Any], key: str = "input") -> "ARCGridAgent":
        if key not in pair:
            raise KeyError(f"task pair missing key {key!r}")
        self.grid = ARCGrid.from_matrix(pair[key])
        return self

    def load_matrix(self, matrix: Sequence[Sequence[int]]) -> "ARCGridAgent":
        self.grid = ARCGrid.from_matrix(matrix)
        return self

    def describe(self) -> str:
        return self.grid.render_full() + "\n\n" + json.dumps(self.grid.describe(), indent=2)

    def describe_json(self) -> Dict[str, Any]:
        return self.grid.describe()

    def get_objects(self) -> Dict[int, List[List[Tuple[int, int]]]]:
        return self.grid.objects_by_color()


def load_task(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def analyze_task(task: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"train": [], "test": []}
    for split in ("train", "test"):
        for index, pair in enumerate(task.get(split, [])):
            row: Dict[str, Any] = {"index": index}
            if "input" in pair:
                row["input"] = ARCGridAgent().load_task_pair(pair, "input").describe_json()
            if "output" in pair:
                row["output"] = ARCGridAgent().load_task_pair(pair, "output").describe_json()
            out[split].append(row)
    return out

# ---------------------------------------------------------------------------
# Visual signatures and online transition memory.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VisualSignature:
    key: str
    raw_hash: str
    braille_hash: str
    braille: Tuple[str, ...]
    point_count: int
    density: float
    bbox: Optional[Dict[str, int]]
    centroid: Optional[Tuple[float, float]]
    quadrant_density: Dict[str, Dict[str, float | int]]
    color_histogram: Tuple[Tuple[str, int], ...]
    changed_points: Tuple[Tuple[int, int], ...]
    changed_count: int
    changed_centroid: Optional[Tuple[float, float]]


@dataclass
class ActionStats:
    tries: int = 0
    progress: int = 0
    regressions: int = 0
    wins: int = 0
    noops: int = 0
    novelty: int = 0
    changed_total: int = 0

    def mean_change(self) -> float:
        return self.changed_total / self.tries if self.tries else 0.0

    def score_prior(self) -> float:
        return (
            self.progress * 20.0
            + self.wins * 100.0
            + self.novelty * 5.0
            + self.mean_change() * 0.05
            - self.noops * 8.0
            - self.regressions * 20.0
        )


@dataclass
class TransitionRecord:
    source_key: str
    action_id: int
    target_key: str
    before_levels: int
    after_levels: int
    changed_count: int
    timestamp: float


class OnlineWorldModel:
    """Small deterministic model of observed state/action outcomes."""

    def __init__(self) -> None:
        self.state_visits: DefaultDict[str, int] = defaultdict(int)
        self.state_action_stats: DefaultDict[Tuple[str, int], ActionStats] = defaultdict(ActionStats)
        self.global_action_stats: DefaultDict[int, ActionStats] = defaultdict(ActionStats)
        self.transitions: Dict[Tuple[str, int], TransitionRecord] = {}
        self.known_states: set[str] = set()
        self.last_level_count: int = 0

    def observe_state(self, state_key: str) -> None:
        self.state_visits[state_key] += 1
        self.known_states.add(state_key)

    def record_transition(
        self,
        source_key: str,
        action_id: int,
        target_key: str,
        before_levels: int,
        after_levels: int,
        changed_count: int,
        is_win: bool,
    ) -> None:
        state_stats = self.state_action_stats[(source_key, action_id)]
        global_stats = self.global_action_stats[action_id]
        for stats in (state_stats, global_stats):
            stats.tries += 1
            stats.changed_total += changed_count
            if after_levels > before_levels:
                stats.progress += after_levels - before_levels
            if after_levels < before_levels:
                stats.regressions += before_levels - after_levels
            if is_win:
                stats.wins += 1
            if target_key == source_key or changed_count == 0:
                stats.noops += 1
            if target_key not in self.known_states:
                stats.novelty += 1
        self.transitions[(source_key, action_id)] = TransitionRecord(
            source_key=source_key,
            action_id=action_id,
            target_key=target_key,
            before_levels=before_levels,
            after_levels=after_levels,
            changed_count=changed_count,
            timestamp=time.time(),
        )
        self.known_states.add(target_key)
        self.last_level_count = max(self.last_level_count, after_levels)


# ---------------------------------------------------------------------------
# Main ARC agent.
# ---------------------------------------------------------------------------
class MyAgent(Agent):
    """ARC-color Braille-sigil ARC-AGI-3 agent with online exploration/world-model policy."""

    MAX_ACTIONS = int(os.getenv("NINE18_MAX_ACTIONS", "80"))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.world = OnlineWorldModel()
        self.last_visual: Optional[VisualSignature] = None
        self.last_state_key: Optional[str] = None
        self.last_levels_completed: int = 0
        self.pending_action_id: Optional[int] = None
        self.pending_action_key: Optional[str] = None
        self.pending_before_levels: int = 0
        self.step_index: int = 0
        self.trace_enabled = os.getenv("NINE18_TRACE", "0").strip().lower() in {"1", "true", "yes"}
        self.trace_path = os.getenv("NINE18_TRACE_PATH", "nine18_braille_agent_trace.jsonl")

    @property
    def name(self) -> str:
        base_name = super().name if hasattr(super(), "name") else self.__class__.__name__.lower()
        return f"{base_name}.arc_color_braille_sigil_v2"

    def is_done(self, frames: List[FrameData], latest_frame: FrameData) -> bool:
        state = getattr(latest_frame, "state", None)
        levels_completed = int(getattr(latest_frame, "levels_completed", 0) or 0)
        win_levels = int(getattr(latest_frame, "win_levels", 0) or 0)
        return any(
            [
                self._state_is(state, "WIN"),
                bool(win_levels and levels_completed >= win_levels),
                bool(getattr(self, "action_counter", 0) >= self.MAX_ACTIONS),
            ]
        )

    def choose_action(self, frames: List[FrameData], latest_frame: FrameData) -> GameAction:
        self.step_index += 1
        visual = self._visual_signature(latest_frame)
        state = getattr(latest_frame, "state", None)
        current_levels = int(getattr(latest_frame, "levels_completed", 0) or 0)

        self._commit_pending_transition(visual, state, current_levels)
        self.world.observe_state(visual.key)

        if self._state_is(state, "NOT_PLAYED") or self._state_is(state, "GAME_OVER"):
            action = GameAction.RESET
            self._attach_reasoning(
                action,
                {
                    "agent": "nine18_arc_color_braille_sigil_v2",
                    "mode": "reset_required",
                    "state": self._state_name(state),
                    "braille_hash": visual.braille_hash,
                },
            )
            self._set_pending(action, visual, current_levels)
            self._trace(latest_frame, visual, action, "reset_required", [])
            return action

        candidates = self._available_actions(latest_frame)
        if not candidates:
            candidates = self._all_non_reset_actions()
        candidates = [action for action in candidates if not self._action_is_reset(action)]
        if not candidates:
            action = GameAction.RESET
            self._attach_reasoning(action, {"agent": "nine18_arc_color_braille_sigil_v2", "mode": "fallback_reset_no_candidates"})
            self._set_pending(action, visual, current_levels)
            self._trace(latest_frame, visual, action, "fallback_reset_no_candidates", [])
            return action

        scored = [(self._score_action(action, visual, current_levels), action) for action in candidates]
        scored.sort(key=lambda item: item[0], reverse=True)
        chosen = scored[0][1]

        if self._is_complex_action(chosen):
            target_x, target_y, target_source = self._choose_target(visual)
            self._set_action_data(chosen, {"x": int(target_x), "y": int(target_y)})
        else:
            target_source = "simple_action_no_coordinates"

        action_id = self._action_id(chosen)
        reasoning = {
            "agent": "nine18_arc_color_braille_sigil_v2",
            "mode": "braille_world_model_ucb",
            "step": self.step_index,
            "state": self._state_name(state),
            "levels_completed": current_levels,
            "known_states": len(self.world.known_states),
            "available_action_ids": [self._action_id(action) for action in candidates],
            "selected_action_id": action_id,
            "selected_action_name": self._action_name(chosen),
            "visual": {
                "raw_hash": visual.raw_hash,
                "braille_hash": visual.braille_hash,
                "point_count": visual.point_count,
                "density": visual.density,
                "bbox": visual.bbox,
                "centroid": visual.centroid,
                "changed_count": visual.changed_count,
                "changed_centroid": visual.changed_centroid,
            },
            "target_source": target_source,
            "scoreboard": [
                {
                    "action_id": self._action_id(action),
                    "action_name": self._action_name(action),
                    "score": round(score, 5),
                    "tries_here": self.world.state_action_stats[(visual.key, self._action_id(action))].tries,
                    "global_tries": self.world.global_action_stats[self._action_id(action)].tries,
                }
                for score, action in scored[: min(7, len(scored))]
            ],
        }
        self._attach_reasoning(chosen, reasoning)
        self._set_pending(chosen, visual, current_levels)
        self._trace(latest_frame, visual, chosen, "selected", scored)
        return chosen

    # ------------------------------------------------------------------
    # Visual processing.
    # ------------------------------------------------------------------
    def _visual_signature(self, latest_frame: FrameData) -> VisualSignature:
        matrix = self._coerce_frame_matrix(getattr(latest_frame, "frame", None))
        raw_hash = self._hash_jsonable(matrix)

        arc_matrix = self._matrix_to_arc_color_matrix(matrix)
        arc_grid = ARCGrid.from_matrix(arc_matrix) if arc_matrix else ARCGrid(1, 1)
        description = arc_grid.describe()
        braille_lines = tuple(description["braille"])
        braille_hash = hashlib.sha256("\n".join(braille_lines).encode("utf-8")).hexdigest()[:24]

        occupied_points = tuple(sorted(arc_grid.occupied_points()))
        point_set = set(occupied_points)
        if self.last_visual is None:
            changed_points = occupied_points
        else:
            previous_points = self._points_from_braille(self.last_visual.braille)
            changed_points = tuple(sorted(point_set.symmetric_difference(previous_points)))

        changed_centroid = self._centroid_tuple(changed_points)
        centroid_dict = description.get("centroid")
        centroid = None
        if centroid_dict is not None:
            centroid = (float(centroid_dict["x"]), float(centroid_dict["y"]))

        histogram_dict = description.get("color_histogram", {})
        histogram = tuple((str(k), int(v)) for k, v in sorted(histogram_dict.items(), key=lambda item: int(item[0])))

        state_key_seed = {
            "raw_hash": raw_hash,
            "braille_hash": braille_hash,
            "levels": int(getattr(latest_frame, "levels_completed", 0) or 0),
            "state": self._state_name(getattr(latest_frame, "state", None)),
            "colors_present": description.get("colors_present", []),
            "objects_per_color": description.get("objects_per_color", {}),
            "symmetry": description.get("symmetry", {}),
        }
        key = hashlib.sha256(json.dumps(state_key_seed, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:32]
        return VisualSignature(
            key=key,
            raw_hash=raw_hash,
            braille_hash=braille_hash,
            braille=braille_lines,
            point_count=int(description["total_colored_cells"]),
            density=float(description["density_overall"]),
            bbox=description.get("bounding_box"),
            centroid=centroid,
            quadrant_density=description.get("quadrant_density", {}),
            color_histogram=histogram,
            changed_points=changed_points,
            changed_count=len(changed_points),
            changed_centroid=changed_centroid,
        )

    def _coerce_frame_matrix(self, frame: Any) -> List[List[Any]]:
        if frame is None:
            return []
        if hasattr(frame, "tolist"):
            frame = frame.tolist()
        if not isinstance(frame, list):
            return [[self._freeze_cell(frame)]]
        if len(frame) == 0:
            return []

        # Normalize 1D frames into a single row; normalize ndarray-like rows.
        if frame and not isinstance(frame[0], (list, tuple)) and not hasattr(frame[0], "tolist"):
            return [[self._freeze_cell(cell) for cell in frame]]

        matrix: List[List[Any]] = []
        for row in frame:
            if hasattr(row, "tolist"):
                row = row.tolist()
            if not isinstance(row, (list, tuple)):
                matrix.append([self._freeze_cell(row)])
                continue
            matrix.append([self._freeze_cell(cell) for cell in row])
        return matrix

    def _freeze_cell(self, value: Any) -> Any:
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple)):
            return tuple(self._freeze_cell(item) for item in value)
        if isinstance(value, dict):
            return tuple(sorted((str(key), self._freeze_cell(val)) for key, val in value.items()))
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value
        return repr(value)

    def _matrix_to_arc_color_matrix(self, matrix: List[List[Any]]) -> List[List[int]]:
        """Convert an arbitrary ARC-AGI-3 frame matrix into a 0..9 ARC color matrix.

        Native integer colors 0..9 are preserved. RGB/tuple/object cells are collapsed
        by deterministic token mapping after treating the most common cell as background 0.
        Frames larger than 64x64 are nearest-neighbor downsampled by ARCGrid.from_matrix.
        """
        if not matrix:
            return []
        height = len(matrix)
        width = max((len(row) for row in matrix), default=0)
        if width <= 0:
            return []

        flat: List[Any] = []
        for row in matrix:
            flat.extend(row)
        background = Counter(flat).most_common(1)[0][0] if flat else 0

        token_to_color: Dict[str, int] = {}
        out: List[List[int]] = []
        for row in matrix:
            out_row: List[int] = []
            for cell in row:
                if cell == background or cell in (None, False, "", "0"):
                    out_row.append(0)
                    continue
                if isinstance(cell, (int, float)) and int(cell) == cell and 0 <= int(cell) <= 9:
                    out_row.append(int(cell))
                    continue
                token = self._cell_to_token(cell)
                if token not in token_to_color:
                    digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
                    candidate = (digest % 9) + 1
                    if candidate in token_to_color.values() and len(set(token_to_color.values())) < 9:
                        for color in range(1, 10):
                            if color not in token_to_color.values():
                                candidate = color
                                break
                    token_to_color[token] = candidate
                out_row.append(token_to_color[token])
            if len(out_row) < width:
                out_row.extend([0] * (width - len(out_row)))
            out.append(out_row)
        return out

    def _matrix_to_64_points(self, matrix: List[List[Any]]) -> Tuple[List[Tuple[int, int]], Tuple[Tuple[str, int], ...]]:
        if not matrix:
            return [], tuple()
        height = len(matrix)
        width = max((len(row) for row in matrix), default=0)
        if width <= 0:
            return [], tuple()

        flat: List[Any] = []
        for row in matrix:
            flat.extend(row)
        background = Counter(flat).most_common(1)[0][0] if flat else 0
        histogram_counter = Counter(self._cell_to_token(cell) for cell in flat)
        histogram = tuple(histogram_counter.most_common(12))

        points: set[Tuple[int, int]] = set()
        for y, row in enumerate(matrix):
            if not row:
                continue
            row_width = len(row)
            for x, cell in enumerate(row):
                if self._is_occupied_cell(cell, background):
                    mapped_x = min(GRID_W - 1, max(0, int((x + 0.5) * GRID_W / max(1, row_width))))
                    mapped_y = min(GRID_H - 1, max(0, int((y + 0.5) * GRID_H / max(1, height))))
                    points.add((mapped_x, mapped_y))
        return sorted(points), histogram

    def _is_occupied_cell(self, cell: Any, background: Any) -> bool:
        if cell == background:
            return False
        if cell in (None, False, 0, "", "0"):
            return False
        if isinstance(cell, tuple) and all(item in (0, 0.0, False, None) for item in cell):
            return False
        return True

    def _cell_to_token(self, cell: Any) -> str:
        if isinstance(cell, tuple):
            return "[" + ",".join(self._cell_to_token(item) for item in cell) + "]"
        return str(cell)

    def _points_from_braille(self, braille_lines: Tuple[str, ...]) -> set[Tuple[int, int]]:
        points: set[Tuple[int, int]] = set()
        for gy, line in enumerate(braille_lines):
            for gx, ch in enumerate(line):
                value = ord(ch) - BRAILLE_BASE
                if value < 0 or value > 255:
                    continue
                for (local_x, local_y), bit in _DOT_BIT.items():
                    if value & (1 << bit):
                        points.add((gx * CELL_W + local_x, gy * CELL_H + local_y))
        return points

    # ------------------------------------------------------------------
    # World-model policy.
    # ------------------------------------------------------------------
    def _commit_pending_transition(self, visual: VisualSignature, state: Any, current_levels: int) -> None:
        if self.pending_action_id is None or self.pending_action_key is None:
            self.last_visual = visual
            self.last_state_key = visual.key
            self.last_levels_completed = current_levels
            return
        self.world.record_transition(
            source_key=self.pending_action_key,
            action_id=self.pending_action_id,
            target_key=visual.key,
            before_levels=self.pending_before_levels,
            after_levels=current_levels,
            changed_count=visual.changed_count,
            is_win=self._state_is(state, "WIN"),
        )
        self.pending_action_id = None
        self.pending_action_key = None
        self.pending_before_levels = 0
        self.last_visual = visual
        self.last_state_key = visual.key
        self.last_levels_completed = current_levels

    def _score_action(self, action: GameAction, visual: VisualSignature, current_levels: int) -> float:
        action_id = self._action_id(action)
        state_stats = self.world.state_action_stats[(visual.key, action_id)]
        global_stats = self.world.global_action_stats[action_id]
        visit_count = max(1, self.world.state_visits[visual.key])
        tries_here = state_stats.tries

        # UCB term: aggressive on untried state-action pairs, calmer after testing.
        if tries_here == 0:
            exploration = 60.0
        else:
            exploration = 12.0 * math.sqrt(math.log(visit_count + 2.0) / (tries_here + 1.0))

        predicted = 0.0
        transition = self.world.transitions.get((visual.key, action_id))
        if transition is not None:
            level_delta = transition.after_levels - transition.before_levels
            predicted += level_delta * 35.0
            predicted += min(25.0, transition.changed_count * 0.05)
            if transition.target_key == visual.key:
                predicted -= 18.0

        global_prior = global_stats.score_prior() * 0.35
        state_prior = state_stats.score_prior() * 0.8
        novelty_pressure = max(0.0, 25.0 - self.world.state_visits[visual.key] * 3.0)
        salience_bonus = 0.0
        if self._is_complex_action(action):
            salience_bonus += 8.0 if visual.bbox or visual.changed_centroid else -4.0
        else:
            salience_bonus += self._deterministic_action_phase_bonus(action_id, visual.key)

        loop_penalty = max(0.0, tries_here - 1.0) * 7.5
        game_progress_bias = current_levels * 0.25
        tie_break = self._stable_float(f"{visual.key}:{action_id}:{self.step_index}") * 0.01
        return (
            exploration
            + predicted
            + global_prior
            + state_prior
            + novelty_pressure
            + salience_bonus
            + game_progress_bias
            + tie_break
            - loop_penalty
        )

    def _deterministic_action_phase_bonus(self, action_id: int, state_key: str) -> float:
        # Keeps exploration from becoming ACTION1-only when every action is new.
        seed = int(hashlib.sha256(f"{state_key}:{self.step_index}".encode("utf-8")).hexdigest()[:8], 16)
        phase = seed % 7
        return 3.0 if action_id == (phase + 1) else 0.0

    def _choose_target(self, visual: VisualSignature) -> Tuple[int, int, str]:
        if visual.changed_centroid is not None and visual.changed_count <= 1024:
            return self._clamp_xy(visual.changed_centroid[0], visual.changed_centroid[1]) + ("changed_centroid",)
        if visual.centroid is not None:
            return self._clamp_xy(visual.centroid[0], visual.centroid[1]) + ("occupancy_centroid",)
        if visual.bbox is not None:
            center_x = (visual.bbox["x_min"] + visual.bbox["x_max"]) / 2.0
            center_y = (visual.bbox["y_min"] + visual.bbox["y_max"]) / 2.0
            return self._clamp_xy(center_x, center_y) + ("bbox_center",)
        return (GRID_W // 2, GRID_H // 2, "grid_center")

    def _clamp_xy(self, x: float, y: float) -> Tuple[int, int]:
        return (
            min(GRID_W - 1, max(0, int(round(x)))),
            min(GRID_H - 1, max(0, int(round(y)))),
        )

    def _set_pending(self, action: GameAction, visual: VisualSignature, current_levels: int) -> None:
        self.pending_action_id = self._action_id(action)
        self.pending_action_key = visual.key
        self.pending_before_levels = current_levels

    # ------------------------------------------------------------------
    # ARC action/state normalization helpers.
    # ------------------------------------------------------------------
    def _available_actions(self, latest_frame: FrameData) -> List[GameAction]:
        raw_available = getattr(latest_frame, "available_actions", None)
        if raw_available is None:
            return self._all_non_reset_actions()
        if isinstance(raw_available, dict):
            raw_items = list(raw_available.values())
        elif isinstance(raw_available, (list, tuple, set)):
            raw_items = list(raw_available)
        else:
            raw_items = [raw_available]

        out: List[GameAction] = []
        seen: set[int] = set()
        for item in raw_items:
            action = self._coerce_action(item)
            if action is None:
                continue
            action_id = self._action_id(action)
            if action_id not in seen:
                seen.add(action_id)
                out.append(action)
        return out

    def _all_non_reset_actions(self) -> List[GameAction]:
        return [action for action in list(GameAction) if not self._action_is_reset(action)]

    def _coerce_action(self, item: Any) -> Optional[GameAction]:
        if isinstance(item, GameAction):
            return item
        candidate_values: List[Any] = []
        if isinstance(item, dict):
            candidate_values.extend([item.get("id"), item.get("value"), item.get("name"), item.get("action")])
        else:
            for attr in ("id", "value", "name", "action"):
                if hasattr(item, attr):
                    candidate_values.append(getattr(item, attr))
            candidate_values.append(item)

        for value in candidate_values:
            if value is None:
                continue
            try:
                if hasattr(GameAction, "from_id") and isinstance(value, (int, float, str)) and str(value).lstrip("-").isdigit():
                    return GameAction.from_id(int(value))  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                if isinstance(value, str) and hasattr(GameAction, value):
                    return getattr(GameAction, value)
            except Exception:
                pass
            try:
                for action in list(GameAction):
                    if value == getattr(action, "value", None) or str(value) == str(getattr(action, "value", "")):
                        return action
                    if str(value).upper() == self._action_name(action).upper():
                        return action
            except Exception:
                pass
        return None

    def _action_id(self, action: GameAction) -> int:
        for attr in ("id", "value"):
            if hasattr(action, attr):
                value = getattr(action, attr)
                try:
                    return int(value)
                except Exception:
                    try:
                        return int(str(value).replace("ACTION", ""))
                    except Exception:
                        continue
        name = self._action_name(action)
        if name == "RESET":
            return 0
        if name.startswith("ACTION"):
            try:
                return int(name.replace("ACTION", ""))
            except Exception:
                pass
        return int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:4], 16)

    def _action_name(self, action: GameAction) -> str:
        return str(getattr(action, "name", str(action))).split(".")[-1]

    def _action_is_reset(self, action: GameAction) -> bool:
        return self._action_name(action).upper() == "RESET" or self._action_id(action) == 0

    def _is_complex_action(self, action: GameAction) -> bool:
        try:
            return bool(action.is_complex())  # type: ignore[attr-defined]
        except Exception:
            return self._action_id(action) == 6 or self._action_name(action).upper() == "ACTION6"

    def _set_action_data(self, action: GameAction, data: Dict[str, Any]) -> None:
        try:
            action.set_data(data)  # type: ignore[attr-defined]
        except Exception:
            setattr(action, "action_data", data)

    def _attach_reasoning(self, action: GameAction, reasoning: Any) -> None:
        try:
            setattr(action, "reasoning", reasoning)
        except Exception:
            pass

    def _state_is(self, state: Any, expected_name: str) -> bool:
        return self._state_name(state).upper() == expected_name.upper()

    def _state_name(self, state: Any) -> str:
        if state is None:
            return "UNKNOWN"
        if hasattr(state, "name"):
            return str(getattr(state, "name"))
        value = getattr(state, "value", state)
        return str(value).split(".")[-1]

    # ------------------------------------------------------------------
    # Utility.
    # ------------------------------------------------------------------
    def _centroid_tuple(self, points: Iterable[Tuple[int, int]]) -> Optional[Tuple[float, float]]:
        pts = list(points)
        if not pts:
            return None
        return (
            round(sum(x for x, _ in pts) / len(pts), 3),
            round(sum(y for _, y in pts) / len(pts), 3),
        )

    def _hash_jsonable(self, value: Any) -> str:
        try:
            payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
        except Exception:
            payload = repr(value)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def _stable_float(self, seed: str) -> float:
        value = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12], 16)
        return value / float(0xFFFFFFFFFFFF)

    def _trace(
        self,
        latest_frame: FrameData,
        visual: VisualSignature,
        action: GameAction,
        mode: str,
        scored: Sequence[Tuple[float, GameAction]],
    ) -> None:
        if not self.trace_enabled:
            return
        row = {
            "t": round(time.time(), 6),
            "game_id": getattr(self, "game_id", getattr(latest_frame, "game_id", "unknown")),
            "step": self.step_index,
            "mode": mode,
            "state": self._state_name(getattr(latest_frame, "state", None)),
            "levels_completed": int(getattr(latest_frame, "levels_completed", 0) or 0),
            "action_id": self._action_id(action),
            "action_name": self._action_name(action),
            "raw_hash": visual.raw_hash,
            "braille_hash": visual.braille_hash,
            "point_count": visual.point_count,
            "density": visual.density,
            "bbox": visual.bbox,
            "centroid": visual.centroid,
            "changed_count": visual.changed_count,
            "known_states": len(self.world.known_states),
            "scores": [
                [round(score, 5), self._action_id(candidate), self._action_name(candidate)]
                for score, candidate in list(scored)[:7]
            ],
        }
        try:
            with open(self.trace_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        except Exception:
            pass


# Alias for the full ARC-AGI-3-Agents repo when importing by class name.
BrailleSigil = MyAgent
