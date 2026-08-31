"""
arc_braille_grid_agent.py

ARC Prize optimized multi-color grid agent.

Features
--------
- Supports ARC colors 0-9.
- Handles variable-size grids up to 64x64, including normal ARC task grids up to 30x30.
- Pads internal storage to 64x64 for deterministic Braille packing.
- Produces Unicode Braille visualization using ISO 11548-1 dot-to-bit packing.
- Extracts objects as connected components per color.
- Computes per-color stats, bounding boxes, centroids, quadrant density, and symmetry.
- Provides common symbolic transforms used by ARC-style solvers.

This module is standalone and can be imported by a solver, used in a CLI, or embedded
inside ARC-AGI-3 agent/my_agent.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple

GRID_W = 64
GRID_H = 64
CELL_W = 2
CELL_H = 4
GLYPH_COLS = GRID_W // CELL_W
GLYPH_ROWS = GRID_H // CELL_H
BRAILLE_BASE = 0x2800

_DOT_BIT: Dict[Tuple[int, int], int] = {
    (0, 0): 0,
    (0, 1): 1,
    (0, 2): 2,
    (1, 0): 3,
    (1, 1): 4,
    (1, 2): 5,
    (0, 3): 6,
    (1, 3): 7,
}

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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze and visualize ARC grids with Unicode Braille.")
    parser.add_argument("input", nargs="?", default="-", help="JSON task file, grid matrix, or '-' for stdin.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of text rendering.")
    parser.add_argument("--pair-index", type=int, default=None, help="Render one train pair index from a full ARC task.")
    parser.add_argument("--key", choices=["input", "output"], default="input", help="Pair key to render when using --pair-index.")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.input == "-" else open(args.input, "r", encoding="utf-8").read()
    data = json.loads(raw)

    if isinstance(data, dict) and "train" in data:
        if args.pair_index is None:
            analysis = analyze_task(data)
            print(json.dumps(analysis, indent=2) if args.json else json.dumps(analysis, indent=2))
            return 0
        pair = data["train"][args.pair_index]
        agent = ARCGridAgent().load_task_pair(pair, args.key)
    else:
        agent = ARCGridAgent().load_matrix(data)

    print(json.dumps(agent.describe_json(), indent=2) if args.json else agent.describe())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
