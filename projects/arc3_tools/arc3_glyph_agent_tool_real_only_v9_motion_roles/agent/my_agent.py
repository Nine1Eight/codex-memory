"""Glyph Flood ARC-AGI-3 Agent.

Self-contained `agent/my_agent.py` for the ARC-AGI-3 Kaggle Starter.

Official framework contract:
    - subclass agents.agent.Agent
    - class name: MyAgent
    - implement is_done(frames, latest_frame) -> bool
    - implement choose_action(frames, latest_frame) -> GameAction

Design:
    - no model weights
    - no network
    - no external dependencies
    - no game-specific hard-coded solution traces
    - pure Python, deterministic fallback behavior
    - flood-fill symbolic vision with 8-dot Braille semantic pixels
    - online action-effect learning
    - explore -> verify -> plan loop

This file is intentionally standalone because the official starter splices this file
into the Kaggle notebook.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
import os
import random
import time
import sys
import types

# Some ARC local runners load this file via importlib.util.module_from_spec()
# + exec_module() without first putting the module object into sys.modules.
# Python 3.12 dataclasses require sys.modules[__name__] to exist during class
# decoration. This shim fixes loader registration only; it does not create any
# fake ARC classes or fallback runtime.
if __name__ not in sys.modules:
    _loader_module = types.ModuleType(__name__)
    _loader_module.__dict__.update(globals())
    sys.modules[__name__] = _loader_module

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Framework imports.
# ---------------------------------------------------------------------------

try:
    from arcengine import FrameData, GameAction, GameState
    from agents.agent import Agent
except Exception as exc:
    raise ImportError(
        "GlyphFloodBraille ARC agent must run inside the real ARC-AGI-3 starter/runtime. "
        "Missing required imports: arcengine.FrameData/GameAction/GameState and agents.agent.Agent. "
        "Install this file into the official starter's agent/my_agent.py, then run the starter's real local runner."
    ) from exc


# ---------------------------------------------------------------------------
# Braille semantic-pixel vocabulary.
# ---------------------------------------------------------------------------

BRAILLE_DOT_BITS: Dict[int, int] = {
    1: 1 << 0,
    2: 1 << 1,
    3: 1 << 2,
    4: 1 << 3,
    5: 1 << 4,
    6: 1 << 5,
    7: 1 << 6,
    8: 1 << 7,
}

GRADE1_LETTER_TO_DOTS: Dict[str, Tuple[int, ...]] = {
    "A": (1,),
    "B": (1, 2),
    "C": (1, 4),
    "D": (1, 4, 5),
    "E": (1, 5),
    "F": (1, 2, 4),
    "G": (1, 2, 4, 5),
    "H": (1, 2, 5),
    "I": (2, 4),
    "J": (2, 4, 5),
    "K": (1, 3),
    "L": (1, 2, 3),
    "M": (1, 3, 4),
    "N": (1, 3, 4, 5),
    "O": (1, 3, 5),
    "P": (1, 2, 3, 4),
    "Q": (1, 2, 3, 4, 5),
    "R": (1, 2, 3, 5),
    "S": (2, 3, 4),
    "T": (2, 3, 4, 5),
    "U": (1, 3, 6),
    "V": (1, 2, 3, 6),
    "W": (2, 4, 5, 6),
    "X": (1, 3, 4, 6),
    "Y": (1, 3, 4, 5, 6),
    "Z": (1, 3, 5, 6),
}


def braille_from_dots(dots: Sequence[int]) -> str:
    mask = 0
    for dot in dots:
        mask |= BRAILLE_DOT_BITS.get(int(dot), 0)
    return chr(0x2800 + mask)


def braille_for_letter(letter: str) -> str:
    letter = letter.strip().upper()
    if letter not in GRADE1_LETTER_TO_DOTS:
        return "⠿"
    return braille_from_dots(GRADE1_LETTER_TO_DOTS[letter])


@dataclass(frozen=True)
class ClassSpec:
    class_id: int
    name: str
    letter: str
    braille: str
    blocking: bool
    traversable: bool
    objective: bool
    controllable: bool


DEFAULT_CLASS_SPECS: Dict[int, ClassSpec] = {
    0: ClassSpec(0, "empty", ".", ".", False, True, False, False),
    1: ClassSpec(1, "wall", "W", braille_for_letter("W"), True, False, False, False),
    2: ClassSpec(2, "player", "P", braille_for_letter("P"), False, True, False, True),
    3: ClassSpec(3, "goal", "G", braille_for_letter("G"), False, True, True, False),
    4: ClassSpec(4, "door", "D", braille_for_letter("D"), True, False, False, False),
    5: ClassSpec(5, "key", "K", braille_for_letter("K"), False, True, False, False),
    6: ClassSpec(6, "enemy", "E", braille_for_letter("E"), True, False, False, False),
    7: ClassSpec(7, "button", "B", braille_for_letter("B"), False, True, False, False),
    8: ClassSpec(8, "artifact", "A", braille_for_letter("A"), False, True, False, False),
    9: ClassSpec(9, "object", "O", braille_for_letter("O"), False, True, False, False),
    10: ClassSpec(10, "water", "W", braille_for_letter("W"), True, False, False, False),
    11: ClassSpec(11, "lava", "L", braille_for_letter("L"), True, False, False, False),
    12: ClassSpec(12, "teleporter", "T", braille_for_letter("T"), False, True, False, False),
    13: ClassSpec(13, "switch", "S", braille_for_letter("S"), False, True, False, False),
    14: ClassSpec(14, "chest", "C", braille_for_letter("C"), False, True, False, False),
    15: ClassSpec(15, "npc", "N", braille_for_letter("N"), False, True, False, False),
}


# ---------------------------------------------------------------------------
# Low-level utilities.
# ---------------------------------------------------------------------------

Grid = List[List[int]]
Point = Tuple[float, float]


def _state_name(state: Any) -> str:
    raw = getattr(state, "name", None)
    if raw is None:
        raw = str(state)
    return str(raw).split(".")[-1].upper()


def _action_name(action: Any) -> str:
    return str(getattr(action, "name", str(action))).split(".")[-1].upper()


def _action_value(action: Any) -> int:
    value = getattr(action, "value", None)
    try:
        return int(value)
    except Exception:
        digits = "".join(ch for ch in _action_name(action) if ch.isdigit())
        return int(digits) if digits else 999


def _is_complex_action(action: Any) -> bool:
    fn = getattr(action, "is_complex", None)
    if callable(fn):
        try:
            return bool(fn())
        except Exception:
            return False
    return False


def _set_action_data(action: Any, data: Dict[str, Any]) -> None:
    fn = getattr(action, "set_data", None)
    if callable(fn):
        try:
            fn(dict(data))
            return
        except Exception:
            pass
    try:
        setattr(action, "data", dict(data))
    except Exception:
        pass


def _set_reasoning(action: Any, reasoning: Any) -> None:
    try:
        setattr(action, "reasoning", reasoning)
    except Exception:
        pass


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name, default)
    except Exception:
        return default


def _json_safe(value: Any, limit: int = 500) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, limit=limit) for v in list(value)[:limit]]
    if isinstance(value, dict):
        return {str(k): _json_safe(v, limit=limit) for k, v in list(value.items())[:limit]}
    return str(value)[:limit]


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _clamp_int(x: float, lo: int, hi: int) -> int:
    if not math.isfinite(float(x)):
        return int(lo)
    return int(max(lo, min(hi, round(float(x)))))


def _stable_hash_grid(grid: Optional[Grid]) -> str:
    if not grid:
        return "empty"
    h = hashlib.sha256()
    for row in grid:
        h.update(bytes([int(v) & 255 for v in row]))
        h.update(b"|")
    return h.hexdigest()[:16]


def _manhattan(a: Point, b: Point) -> float:
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def _action_index(action: Any) -> int:
    name = _action_name(action)
    digits = "".join(ch for ch in name if ch.isdigit())
    if digits:
        try:
            return int(digits)
        except Exception:
            pass
    return _action_value(action)


def _looks_like_directional_action(name: str) -> bool:
    upper = name.upper()
    return any(token in upper for token in ("UP", "DOWN", "LEFT", "RIGHT"))


@dataclass
class ReflectionCandidate:
    first_action_name: str
    sequence: Tuple[str, ...]
    score: float
    predicted_position: Point
    predicted_distance: float
    token_cost: int
    expected_reward: float
    remaining_bonus: float
    reason: str


# ---------------------------------------------------------------------------
# Observation extraction.
# ---------------------------------------------------------------------------

class ObservationExtractor:
    """Extract a small integer grid from the many frame shapes seen locally/Kaggle."""

    GRID_ATTRS = (
        "grid",
        "board",
        "cells",
        "matrix",
        "state_grid",
        "observation",
        "obs",
        "frame",
        "image",
        "rgb",
        "pixels",
        "screen",
    )

    DICT_KEYS = (
        "grid",
        "board",
        "cells",
        "matrix",
        "state_grid",
        "observation",
        "obs",
        "frame",
        "image",
        "rgb",
        "pixels",
        "screen",
    )

    def extract(self, frame: Any) -> Optional[Grid]:
        for candidate in self._candidate_values(frame, depth=0):
            grid = self._coerce_to_grid(candidate)
            if grid is not None:
                return grid
        return None

    def _candidate_values(self, value: Any, depth: int) -> Iterable[Any]:
        if depth > 3:
            return

        yield value

        if isinstance(value, dict):
            for key in self.DICT_KEYS:
                if key in value:
                    yield value[key]
            for nested_key in ("data", "payload", "state", "game_state", "info"):
                if nested_key in value:
                    yield from self._candidate_values(value[nested_key], depth + 1)
            return

        to_dict = _safe_getattr(value, "to_dict")
        if callable(to_dict):
            try:
                d = to_dict()
                if isinstance(d, dict):
                    yield from self._candidate_values(d, depth + 1)
            except Exception:
                pass

        model_dump = _safe_getattr(value, "model_dump")
        if callable(model_dump):
            try:
                d = model_dump()
                if isinstance(d, dict):
                    yield from self._candidate_values(d, depth + 1)
            except Exception:
                pass

        for attr in self.GRID_ATTRS:
            child = _safe_getattr(value, attr, None)
            if child is not None:
                yield child

        for attr in ("data", "payload", "state_data", "game_state", "info"):
            child = _safe_getattr(value, attr, None)
            if child is not None:
                yield from self._candidate_values(child, depth + 1)

    def _coerce_to_grid(self, value: Any) -> Optional[Grid]:
        if value is None:
            return None

        # Numpy-like arrays.
        shape = _safe_getattr(value, "shape", None)
        tolist = _safe_getattr(value, "tolist", None)
        if shape is not None and callable(tolist):
            try:
                value = tolist()
            except Exception:
                return None

        if isinstance(value, str):
            return self._grid_from_text(value)

        if isinstance(value, dict):
            for key in self.DICT_KEYS:
                if key in value:
                    grid = self._coerce_to_grid(value[key])
                    if grid is not None:
                        return grid
            return None

        if isinstance(value, (list, tuple)):
            return self._grid_from_nested_list(value)

        return None

    def _grid_from_text(self, text: str) -> Optional[Grid]:
        lines = [line.rstrip("\n") for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        symbol = {
            ".": 0,
            "_": 0,
            " ": 0,
            "W": 1,
            "#": 1,
            "P": 2,
            "@": 2,
            "G": 3,
            "*": 3,
            "D": 4,
            "K": 5,
            "E": 6,
            "B": 7,
            "U": 8,
            "O": 9,
        }

        grid: Grid = []
        for line in lines:
            stripped = line.strip()
            if "," in stripped:
                parts = [p for p in stripped.split(",") if p.strip()]
                try:
                    row = [int(float(p.strip())) for p in parts]
                except Exception:
                    return None
            elif " " in stripped and all(part.lstrip("-").isdigit() for part in stripped.split()):
                row = [int(part) for part in stripped.split()]
            else:
                row = []
                for ch in stripped:
                    if ch.isdigit():
                        row.append(int(ch))
                    else:
                        row.append(symbol.get(ch.upper(), 9))
            if row:
                grid.append(row)

        return self._validate_grid(grid)

    def _grid_from_nested_list(self, value: Sequence[Any]) -> Optional[Grid]:
        if not value:
            return None

        # Real ARC FrameData can expose frame as C x H x W, for example
        # len(frame)=1, len(frame[0])=64, len(frame[0][0])=64. Treat that as
        # one channel of a 64x64 integer grid, not as a 1x64 RGB image.
        chw = self._grid_from_channel_first(value)
        if chw is not None:
            return chw

        # H x W integer grid.
        if all(isinstance(row, (list, tuple)) for row in value):
            first = value[0]
            if not isinstance(first, (list, tuple)) or not first:
                return None

            # RGB/RGBA image: H x W x C. Only use this branch when pixels
            # look like short color tuples/lists, not long 64-wide rows.
            if all(isinstance(px, (list, tuple)) for px in first):
                first_px = first[0] if first else None
                if isinstance(first_px, (list, tuple)) and 3 <= len(first_px) <= 4:
                    return self._quantize_image(value)
                nested = self._grid_from_channel_first(value)
                if nested is not None:
                    return nested
                return None

            # Plain 2D grid.
            grid: Grid = []
            try:
                for row in value:
                    out_row = []
                    for v in row:
                        if _is_number(v):
                            out_row.append(int(v))
                        elif isinstance(v, str) and v.strip().lstrip("-").isdigit():
                            out_row.append(int(v.strip()))
                        else:
                            return None
                    grid.append(out_row)
            except Exception:
                return None
            return self._validate_grid(grid)

        # Flat list cannot safely infer shape.
        return None

    def _grid_from_channel_first(self, value: Sequence[Any]) -> Optional[Grid]:
        """Coerce CxHxW numeric frame into HxW grid.

        The real tr87 probe showed FrameData.frame as list[list[list[int]]]
        with outer length 1, middle length 64, inner length 64. That is a
        channel-first single-plane frame and must be unwrapped before
        flood-fill vision.
        """
        if not isinstance(value, (list, tuple)) or not value:
            return None

        if len(value) not in (1, 2, 3, 4):
            return None

        first_channel = value[0]
        if not isinstance(first_channel, (list, tuple)) or not first_channel:
            return None

        if not all(isinstance(row, (list, tuple)) for row in first_channel):
            return None

        width = len(first_channel[0])
        height = len(first_channel)
        if width <= 0 or height <= 0:
            return None

        # Require long rows so HxWxRGB one-row screenshots do not get mistaken
        # for channel-first. The ARC probe row width was 64.
        if width < 8 or height < 8:
            return None

        grid: Grid = []
        try:
            for row in first_channel:
                if len(row) != width:
                    return None
                out_row = []
                for v in row:
                    if _is_number(v):
                        out_row.append(int(v))
                    elif isinstance(v, str) and v.strip().lstrip("-").isdigit():
                        out_row.append(int(v.strip()))
                    else:
                        return None
                grid.append(out_row)
        except Exception:
            return None

        return self._validate_grid(grid)

    def _quantize_image(self, image: Sequence[Any]) -> Optional[Grid]:
        """Quantize HxWxC RGB-ish pixels into small integer classes."""
        palette: List[Tuple[int, int, int]] = []
        rows: Grid = []
        tolerance = int(os.environ.get("ARC3_COLOR_TOLERANCE", "24"))
        max_colors = int(os.environ.get("ARC3_MAX_COLORS", "32"))

        def pixel3(px: Any) -> Optional[Tuple[int, int, int]]:
            if not isinstance(px, (list, tuple)) or len(px) < 3:
                return None
            try:
                return (int(px[0]), int(px[1]), int(px[2]))
            except Exception:
                return None

        def dist(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
            return (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])) / 3.0

        raw_ids: List[int] = []
        widths: List[int] = []

        for row in image:
            if not isinstance(row, (list, tuple)):
                return None
            widths.append(len(row))
            for px in row:
                p = pixel3(px)
                if p is None:
                    return None
                assigned = None
                for idx, color in enumerate(palette):
                    if dist(p, color) <= tolerance:
                        assigned = idx
                        break
                if assigned is None:
                    if len(palette) >= max_colors and palette:
                        assigned = min(range(len(palette)), key=lambda i: dist(p, palette[i]))
                    else:
                        palette.append(p)
                        assigned = len(palette) - 1
                raw_ids.append(int(assigned))

        if not widths or len(set(widths)) != 1:
            return None

        counts = Counter(raw_ids)
        dominant = counts.most_common(1)[0][0]
        remap: Dict[int, int] = {dominant: 0}
        next_id = 1
        for old in sorted(set(raw_ids)):
            if old == dominant:
                continue
            remap[old] = next_id
            next_id += 1

        width = widths[0]
        remapped = [remap[v] for v in raw_ids]
        for y in range(len(widths)):
            rows.append(remapped[y * width:(y + 1) * width])

        return self._validate_grid(rows)

    def _validate_grid(self, grid: Optional[Grid]) -> Optional[Grid]:
        if not grid:
            return None
        width = len(grid[0])
        if width <= 0:
            return None
        if any(len(row) != width for row in grid):
            return None
        height = len(grid)
        if height > 256 or width > 256:
            # The ARC games usually expose compact grids/screens. Reject huge
            # raw images because action latency matters.
            return None
        return [[int(v) for v in row] for row in grid]


# ---------------------------------------------------------------------------
# Glyph flood vision.
# ---------------------------------------------------------------------------

@dataclass
class GlyphObject:
    object_id: int
    class_id: int
    class_name: str
    letter: str
    braille: str
    bbox: Tuple[int, int, int, int]
    area: int
    centroid: Point
    density: float
    perimeter: int
    glyph_hash: str
    glyph_rows: Tuple[str, ...]
    affordances: Tuple[str, ...]


@dataclass
class Scene:
    width: int
    height: int
    grid_hash: str
    braille_map: str
    class_counts: Dict[int, int]
    objects: List[GlyphObject]
    actor: Optional[GlyphObject]
    target: Optional[GlyphObject]


class GlyphFloodVision:
    """Flood-fill symbolic scene extractor."""

    def __init__(self, specs: Optional[Dict[int, ClassSpec]] = None, background_id: int = 0, connectivity: int = 4) -> None:
        self.specs = specs or DEFAULT_CLASS_SPECS
        self.background_id = background_id
        self.connectivity = 4 if connectivity not in (4, 8) else connectivity
        self.glyph_w = 8
        self.glyph_h = 8

    def spec(self, class_id: int) -> ClassSpec:
        return self.specs.get(
            class_id,
            ClassSpec(class_id, f"unknown_{class_id}", "?", "⠿", False, True, False, False),
        )

    def analyze(self, grid: Optional[Grid]) -> Optional[Scene]:
        if not grid or not grid[0]:
            return None

        h = len(grid)
        w = len(grid[0])
        objects = self.objects(grid)
        braille_map = "\n".join("".join(self.spec(v).braille for v in row) for row in grid)
        counts: Dict[int, int] = dict(Counter(v for row in grid for v in row))
        actor = self.infer_actor(objects)
        target = self.infer_target(objects, actor)

        return Scene(
            width=w,
            height=h,
            grid_hash=_stable_hash_grid(grid),
            braille_map=braille_map,
            class_counts=counts,
            objects=objects,
            actor=actor,
            target=target,
        )

    def neighbors(self, y: int, x: int, h: int, w: int) -> Iterable[Tuple[int, int]]:
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if self.connectivity == 8:
            offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
        for dy, dx in offsets:
            ny = y + dy
            nx = x + dx
            if 0 <= ny < h and 0 <= nx < w:
                yield ny, nx

    def objects(self, grid: Grid) -> List[GlyphObject]:
        h = len(grid)
        w = len(grid[0])
        visited = [[False for _ in range(w)] for _ in range(h)]
        out: List[GlyphObject] = []

        for y in range(h):
            for x in range(w):
                if visited[y][x]:
                    continue

                class_id = int(grid[y][x])
                if class_id == self.background_id:
                    visited[y][x] = True
                    continue

                q: Deque[Tuple[int, int]] = deque([(y, x)])
                visited[y][x] = True
                comp: List[Tuple[int, int]] = []

                while q:
                    cy, cx = q.popleft()
                    comp.append((cy, cx))
                    for ny, nx in self.neighbors(cy, cx, h, w):
                        if not visited[ny][nx] and int(grid[ny][nx]) == class_id:
                            visited[ny][nx] = True
                            q.append((ny, nx))

                out.append(self._component_to_object(len(out), class_id, comp))

        return out

    def _component_to_object(self, object_id: int, class_id: int, comp: Sequence[Tuple[int, int]]) -> GlyphObject:
        ys = [p[0] for p in comp]
        xs = [p[1] for p in comp]
        min_y, max_y = min(ys), max(ys)
        min_x, max_x = min(xs), max(xs)
        bw = max_x - min_x + 1
        bh = max_y - min_y + 1
        area = len(comp)
        density = area / max(1, bw * bh)
        centroid = (sum(xs) / area, sum(ys) / area)

        mask = [[0 for _ in range(bw)] for _ in range(bh)]
        for y, x in comp:
            mask[y - min_y][x - min_x] = 1

        normalized = self._resize_mask(mask, self.glyph_h, self.glyph_w)
        bits = "".join("1" if cell else "0" for row in normalized for cell in row)
        gh = hashlib.sha256(bits.encode("utf-8")).hexdigest()[:16]
        rows = tuple("".join("█" if cell else "." for cell in row) for row in normalized)
        component_set = set(comp)
        perimeter = 0
        for y, x in comp:
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (y + dy, x + dx) not in component_set:
                    perimeter += 1

        spec = self.spec(class_id)
        affordances: List[str] = []
        if spec.blocking:
            affordances.append("blocks_movement")
        if spec.traversable:
            affordances.append("traversable")
        if spec.objective:
            affordances.append("objective")
        if spec.controllable:
            affordances.append("controlled_actor")
        if not affordances:
            affordances.append("observable")

        return GlyphObject(
            object_id=object_id,
            class_id=class_id,
            class_name=spec.name,
            letter=spec.letter,
            braille=spec.braille,
            bbox=(min_x, min_y, max_x, max_y),
            area=area,
            centroid=(float(centroid[0]), float(centroid[1])),
            density=float(density),
            perimeter=int(perimeter),
            glyph_hash=gh,
            glyph_rows=rows,
            affordances=tuple(affordances),
        )

    def _resize_mask(self, mask: List[List[int]], dst_h: int, dst_w: int) -> List[List[int]]:
        src_h = len(mask)
        src_w = len(mask[0]) if src_h else 0
        if src_h == 0 or src_w == 0:
            return [[0 for _ in range(dst_w)] for _ in range(dst_h)]

        out: List[List[int]] = []
        for gy in range(dst_h):
            sy = 0 if dst_h == 1 else int(round((gy / (dst_h - 1)) * (src_h - 1)))
            row: List[int] = []
            for gx in range(dst_w):
                sx = 0 if dst_w == 1 else int(round((gx / (dst_w - 1)) * (src_w - 1)))
                row.append(1 if mask[sy][sx] else 0)
            out.append(row)
        return out

    def infer_actor(self, objects: Sequence[GlyphObject]) -> Optional[GlyphObject]:
        controllable = [o for o in objects if "controlled_actor" in o.affordances]
        if controllable:
            return sorted(controllable, key=lambda o: (o.area, o.object_id))[0]

        # Unknown games often encode the movable actor as a small, non-wall object.
        candidates = [
            o for o in objects
            if "blocks_movement" not in o.affordances and o.area <= 25
        ]
        if candidates:
            return sorted(candidates, key=lambda o: (o.area, o.perimeter, o.object_id))[0]
        return None

    def infer_target(self, objects: Sequence[GlyphObject], actor: Optional[GlyphObject]) -> Optional[GlyphObject]:
        if not objects:
            return None

        objective = [o for o in objects if "objective" in o.affordances]
        if actor is not None and objective:
            return min(objective, key=lambda o: _manhattan(actor.centroid, o.centroid))
        if objective:
            return objective[0]

        # Prefer key/button/door-like or small non-actor objects.
        priority_letters = {"G": 0, "K": 1, "B": 2, "D": 3, "O": 4, "E": 5}
        candidates = [
            o for o in objects
            if actor is None or o.object_id != actor.object_id
        ]
        if not candidates:
            return None

        def key(o: GlyphObject) -> Tuple[float, float, int]:
            base = priority_letters.get(str(o.letter).upper(), 10)
            dist = _manhattan(actor.centroid, o.centroid) if actor is not None else 0.0
            # Small/compact objects are more likely to matter than huge walls.
            return (base, dist + 0.05 * o.area, o.object_id)

        return min(candidates, key=key)


# ---------------------------------------------------------------------------
# BVS NavigationGraph / A* route layer.
# ---------------------------------------------------------------------------

@dataclass
class RoutePlan:
    path: List[Tuple[int, int]]
    next_cell: Tuple[int, int]
    desired_delta: Point
    target_cells: int
    cost: float


class BVSNavigationPlanner:
    """NavigationGraph/A* over the semantic-pixel grid.

    This implements the BVS layer after flood-fill: the grid is converted into
    a traversability graph, A* finds the path from controlled actor to objective,
    and learned real action vectors are used to select the controller action
    that best follows the route.
    """

    def __init__(self, specs: Optional[Dict[int, ClassSpec]] = None) -> None:
        self.specs = specs or DEFAULT_CLASS_SPECS
        self.enabled = os.environ.get("ARC3_BVS_ASTAR_ENABLED", "1").strip() != "0"
        self.max_targets = int(os.environ.get("ARC3_BVS_MAX_TARGET_CELLS", "512"))
        self.last_diagnostic: Dict[str, Any] = {}

    def choose(
        self,
        grid: Optional[Grid],
        scene: Optional[Scene],
        model: "OnlineWorldModel",
        actions: Sequence[Any],
    ) -> Optional[Tuple[Any, Dict[str, Any]]]:
        self.last_diagnostic = {"enabled": self.enabled}
        if not self.enabled:
            self.last_diagnostic["reason"] = "disabled"
            return None
        if not grid or scene is None or scene.actor is None or scene.target is None:
            self.last_diagnostic["reason"] = "missing_grid_actor_or_target"
            return None

        route = self._plan(grid, scene)
        if route is None or len(route.path) < 2:
            self.last_diagnostic = {
                "enabled": True,
                "reason": "no_astar_route",
                "actor": scene.actor.centroid if scene.actor is not None else None,
                "target": scene.target.centroid if scene.target is not None else None,
                "actor_class": scene.actor.class_name if scene.actor is not None else None,
                "target_class": scene.target.class_name if scene.target is not None else None,
            }
            return None

        action_choice = self._action_for_delta(model, actions, route.desired_delta)
        if action_choice is None:
            self.last_diagnostic = {
                "enabled": True,
                "reason": "no_learned_action_vector_for_route_delta",
                "desired_delta": route.desired_delta,
                "path_length": len(route.path),
                "candidate_actions": [_action_name(a) for a in actions],
                "known_vectors": {
                    name: model.stats[name].vector()
                    for name in sorted(model.stats)
                    if model.stats[name].vector() is not None
                },
            }
            return None

        action, score, vector = action_choice
        stat = model.stats[_action_name(action)]
        self.last_diagnostic = {
            "enabled": True,
            "reason": "route_action_selected",
            "path_length": len(route.path),
            "desired_delta": route.desired_delta,
            "action": _action_name(action),
        }

        return action, {
            "mode": "bvs_astar_route_plan",
            "route": {
                "path_length": len(route.path),
                "next_cell": route.next_cell,
                "desired_delta": route.desired_delta,
                "target_cells": route.target_cells,
                "cost": route.cost,
                "path_head": route.path[:12],
            },
            "action_mapping": {
                "action": _action_name(action),
                "score": score,
                "learned_vector": vector,
                "tries": stat.tries,
                "changed": stat.changed,
                "avg_progress": stat.avg_progress(),
                "positive_progress": stat.positive_progress,
                "negative_progress": stat.negative_progress,
            },
        }

    def _spec(self, class_id: int) -> ClassSpec:
        return self.specs.get(class_id, ClassSpec(class_id, f"unknown_{class_id}", "?", "⠿", False, True, False, False))

    def _is_passable(self, grid: Grid, x: int, y: int, scene: Scene) -> bool:
        v = int(grid[y][x])
        if scene.actor is not None and v == int(scene.actor.class_id):
            return True
        if scene.target is not None and v == int(scene.target.class_id):
            return True
        return bool(self._spec(v).traversable) and not bool(self._spec(v).blocking)

    def _object_cells(self, grid: Grid, obj: GlyphObject) -> List[Tuple[int, int]]:
        min_x, min_y, max_x, max_y = obj.bbox
        cells: List[Tuple[int, int]] = []
        h = len(grid)
        w = len(grid[0]) if h else 0
        for y in range(max(0, min_y), min(h - 1, max_y) + 1):
            for x in range(max(0, min_x), min(w - 1, max_x) + 1):
                if int(grid[y][x]) == int(obj.class_id):
                    cells.append((x, y))
                    if len(cells) >= self.max_targets:
                        return cells
        return cells

    def _nearest_object_cell(self, grid: Grid, obj: GlyphObject) -> Tuple[int, int]:
        h = len(grid)
        w = len(grid[0]) if h else 0
        cx = _clamp_int(obj.centroid[0], 0, max(0, w - 1))
        cy = _clamp_int(obj.centroid[1], 0, max(0, h - 1))

        cells = self._object_cells(grid, obj)
        if not cells:
            return (cx, cy)

        return min(cells, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))

    def _target_cells(self, grid: Grid, scene: Scene, start: Tuple[int, int]) -> List[Tuple[int, int]]:
        if scene.target is None:
            return []
        cells = self._object_cells(grid, scene.target)
        if not cells:
            cells = [self._nearest_object_cell(grid, scene.target)]

        # Keep the target set compact for A*. Nearby objective cells are enough.
        cells.sort(key=lambda p: abs(p[0] - start[0]) + abs(p[1] - start[1]))
        return cells[: self.max_targets]

    def _plan(self, grid: Grid, scene: Scene) -> Optional[RoutePlan]:
        h = len(grid)
        w = len(grid[0]) if h else 0
        if h <= 0 or w <= 0:
            return None
        if scene.actor is None or scene.target is None:
            return None

        start = self._nearest_object_cell(grid, scene.actor)
        targets = self._target_cells(grid, scene, start)
        if not targets:
            return None

        target_set = set(targets)

        def heuristic(p: Tuple[int, int]) -> int:
            return min(abs(p[0] - tx) + abs(p[1] - ty) for tx, ty in target_set)

        pq: List[Tuple[float, int, Tuple[int, int]]] = []
        heapq.heappush(pq, (float(heuristic(start)), 0, start))
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        g_score: Dict[Tuple[int, int], int] = {start: 0}

        found: Optional[Tuple[int, int]] = None
        expansions = 0
        max_expansions = w * h * 4

        while pq and expansions < max_expansions:
            _, cost, current = heapq.heappop(pq)
            expansions += 1

            if current in target_set and current != start:
                found = current
                break

            x, y = current
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx = x + dx
                ny = y + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                np = (nx, ny)
                if np not in target_set and not self._is_passable(grid, nx, ny, scene):
                    continue

                new_cost = cost + 1
                if new_cost < g_score.get(np, 1_000_000_000):
                    g_score[np] = new_cost
                    came_from[np] = current
                    priority = float(new_cost + heuristic(np))
                    heapq.heappush(pq, (priority, new_cost, np))

        if found is None:
            return None

        path: List[Tuple[int, int]] = []
        cur: Optional[Tuple[int, int]] = found
        while cur is not None:
            path.append(cur)
            cur = came_from.get(cur)
        path.reverse()

        if len(path) < 2:
            return None

        next_cell = path[1]
        desired_delta = (float(next_cell[0] - start[0]), float(next_cell[1] - start[1]))
        return RoutePlan(path=path, next_cell=next_cell, desired_delta=desired_delta, target_cells=len(targets), cost=float(len(path) - 1))

    def _action_for_delta(
        self,
        model: "OnlineWorldModel",
        actions: Sequence[Any],
        desired: Point,
    ) -> Optional[Tuple[Any, float, Point]]:
        dx, dy = desired
        dlen = math.sqrt(dx * dx + dy * dy)
        if dlen <= 1e-9:
            return None

        candidates: List[Tuple[float, Any, Point]] = []
        recent = Counter(model.recent_actions)

        for action in actions:
            if _is_complex_action(action):
                continue

            name = _action_name(action)
            stat = model.stats[name]
            vec = stat.vector()
            if vec is None:
                continue

            vx, vy = vec
            vlen = math.sqrt(vx * vx + vy * vy)
            if vlen <= 1e-9:
                continue

            alignment = (vx * dx + vy * dy) / (vlen * dlen)
            score = alignment
            score += 0.25 * stat.success_rate()
            score += 0.20 * stat.progress_confidence()
            score += 0.05 * stat.avg_progress()
            score -= 0.10 * recent[name]
            score -= 0.15 * stat.negative_progress

            if score > -0.25:
                candidates.append((score, action, vec))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        score, action, vec = candidates[0]
        return action, float(score), vec


# ---------------------------------------------------------------------------
# Online world model.
# ---------------------------------------------------------------------------

@dataclass
class ActionStats:
    tries: int = 0
    changed: int = 0
    wins: int = 0
    total_dx: float = 0.0
    total_dy: float = 0.0
    total_progress: float = 0.0
    positive_progress: int = 0
    negative_progress: int = 0
    last_used_step: int = -999_999

    def vector(self) -> Optional[Point]:
        if self.changed <= 0:
            return None
        return (self.total_dx / self.changed, self.total_dy / self.changed)

    def success_rate(self) -> float:
        if self.tries <= 0:
            return 0.0
        return self.changed / self.tries

    def avg_progress(self) -> float:
        if self.tries <= 0:
            return 0.0
        return self.total_progress / self.tries

    def progress_confidence(self) -> float:
        if self.tries <= 0:
            return 0.0
        return self.positive_progress / self.tries


class OnlineWorldModel:
    """Learns action effects from consecutive frames."""

    def __init__(self) -> None:
        self.stats: Dict[str, ActionStats] = defaultdict(ActionStats)
        self.visits: Counter[str] = Counter()
        self.prev_scene: Optional[Scene] = None
        self.prev_action_name: Optional[str] = None
        self.prev_actor_centroid: Optional[Point] = None
        self.step: int = 0
        self.stagnation: int = 0
        self.last_hash: Optional[str] = None
        self.recent_actions: Deque[str] = deque(maxlen=12)
        self.motion_actor_class_id: Optional[int] = None
        self.motion_actor_object_id: Optional[int] = None
        self.last_motion_role_reason: Dict[str, Any] = {}

    def update_before_decision(self, scene: Optional[Scene], latest_state_name: str) -> None:
        self.step += 1

        # Apply dynamic role inference before progress/vector accounting.  The
        # generic BVS class table is useful, but ARC game IDs are not guaranteed
        # to mean "2=player, 3=goal".  The real actor is the object whose
        # centroid changes after our action.
        if scene is not None:
            self._apply_motion_roles(scene)

        if scene is not None:
            self.visits[scene.grid_hash] += 1
            if scene.grid_hash == self.last_hash:
                self.stagnation += 1
            else:
                self.stagnation = 0
            self.last_hash = scene.grid_hash

        if self.prev_action_name is not None:
            stat = self.stats[self.prev_action_name]
            stat.tries += 1
            if latest_state_name == "WIN":
                stat.wins += 1

            if (
                self.prev_scene is not None
                and scene is not None
                and self.prev_scene.actor is not None
                and self.prev_scene.target is not None
                and scene.actor is not None
                and scene.target is not None
            ):
                prev_distance = _manhattan(self.prev_scene.actor.centroid, self.prev_scene.target.centroid)
                current_distance = _manhattan(scene.actor.centroid, scene.target.centroid)
                progress = prev_distance - current_distance
                stat.total_progress += float(progress)
                if progress > 0.05:
                    stat.positive_progress += 1
                elif progress < -0.05:
                    stat.negative_progress += 1

            prev_centroid = self.prev_actor_centroid
            current_centroid = scene.actor.centroid if scene is not None and scene.actor is not None else None
            if prev_centroid is not None and current_centroid is not None:
                dx = current_centroid[0] - prev_centroid[0]
                dy = current_centroid[1] - prev_centroid[1]
                if abs(dx) + abs(dy) > 0.01:
                    stat.changed += 1
                    stat.total_dx += dx
                    stat.total_dy += dy
            elif self.prev_scene is not None and scene is not None and self.prev_scene.grid_hash != scene.grid_hash:
                # We changed the world but could not localize actor motion.
                stat.changed += 1

            elif self.prev_scene is not None and scene is not None and self.prev_scene.grid_hash == scene.grid_hash:
                # Explicitly keep no-change attempts distinguishable.  The
                # denominator still grows via tries; changed remains unchanged.
                pass

        self.prev_scene = scene
        self.prev_actor_centroid = scene.actor.centroid if scene is not None and scene.actor is not None else None

    def _apply_motion_roles(self, scene: Scene) -> None:
        reason: Dict[str, Any] = {
            "enabled": True,
            "source": "static_bvs_fallback",
        }

        motion_actor = self._infer_motion_actor(scene)
        if motion_actor is not None:
            scene.actor = motion_actor
            self.motion_actor_class_id = int(motion_actor.class_id)
            self.motion_actor_object_id = int(motion_actor.object_id)
            reason = {
                "enabled": True,
                "source": "motion_object",
                "actor_object_id": motion_actor.object_id,
                "actor_class_id": motion_actor.class_id,
                "actor_class_name": motion_actor.class_name,
                "actor_area": motion_actor.area,
                "actor_centroid": motion_actor.centroid,
            }
        elif self.motion_actor_class_id is not None:
            # Keep following the same moving class when exact object matching is
            # temporarily ambiguous.
            candidates = [o for o in scene.objects if int(o.class_id) == int(self.motion_actor_class_id)]
            if candidates:
                prev_centroid = self.prev_actor_centroid
                if prev_centroid is not None:
                    actor = min(candidates, key=lambda o: _manhattan(o.centroid, prev_centroid))
                else:
                    actor = min(candidates, key=lambda o: (o.area, o.object_id))
                scene.actor = actor
                reason = {
                    "enabled": True,
                    "source": "motion_class_memory",
                    "actor_object_id": actor.object_id,
                    "actor_class_id": actor.class_id,
                    "actor_class_name": actor.class_name,
                    "actor_area": actor.area,
                    "actor_centroid": actor.centroid,
                }

        if scene.actor is not None:
            dynamic_target = self._infer_dynamic_target(scene, scene.actor)
            if dynamic_target is not None:
                scene.target = dynamic_target
                reason["target_object_id"] = dynamic_target.object_id
                reason["target_class_id"] = dynamic_target.class_id
                reason["target_class_name"] = dynamic_target.class_name
                reason["target_area"] = dynamic_target.area
                reason["target_centroid"] = dynamic_target.centroid

        self.last_motion_role_reason = reason

    def _infer_motion_actor(self, scene: Scene) -> Optional[GlyphObject]:
        if self.prev_scene is None or not self.prev_scene.objects or not scene.objects:
            return None

        candidates: List[Tuple[float, GlyphObject, Dict[str, Any]]] = []
        prev_by_class: Dict[int, List[GlyphObject]] = defaultdict(list)
        for obj in self.prev_scene.objects:
            prev_by_class[int(obj.class_id)].append(obj)

        for cur in scene.objects:
            cid = int(cur.class_id)
            prev_candidates = prev_by_class.get(cid, [])
            small_bonus = 2.0 / max(1.0, math.sqrt(float(cur.area)))
            controllable_penalty = 0.0

            # Huge texture/terrain components are rarely the controlled actor.
            if cur.area > max(32, (scene.width * scene.height) // 20):
                controllable_penalty += 5.0

            if prev_candidates:
                prev = min(prev_candidates, key=lambda p: _manhattan(p.centroid, cur.centroid) + 0.01 * abs(p.area - cur.area))
                movement = _manhattan(prev.centroid, cur.centroid)
                area_delta = abs(prev.area - cur.area)
                score = 5.0 * movement + 0.02 * area_delta + small_bonus - controllable_penalty
                if movement > 0.05 or (cur.area <= 16 and area_delta > 0):
                    candidates.append((score, cur, {"movement": movement, "area_delta": area_delta, "prev": prev.object_id}))
            else:
                # Appearing small singleton/pawn after an action is often the
                # controlled object, especially in tr87 where class 4 appears as
                # a single cell after early moves.
                if cur.area <= 16:
                    score = 3.0 + small_bonus
                    candidates.append((score, cur, {"appeared": True}))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        best_score, best_obj, info = candidates[0]
        if best_score <= 0.25:
            return None

        return best_obj

    def _infer_dynamic_target(self, scene: Scene, actor: GlyphObject) -> Optional[GlyphObject]:
        candidates = [o for o in scene.objects if o.object_id != actor.object_id]
        if not candidates:
            return None

        # Keep an existing static objective only when it is not a giant terrain
        # component.  Otherwise choose a compact reachable-looking object.
        if scene.target is not None and scene.target.object_id != actor.object_id:
            if scene.target.area <= max(128, (scene.width * scene.height) // 8):
                return scene.target

        def score(o: GlyphObject) -> Tuple[float, float, float, int]:
            dist = _manhattan(actor.centroid, o.centroid)
            area = float(o.area)
            compact = area / max(1.0, float((o.bbox[2] - o.bbox[0] + 1) * (o.bbox[3] - o.bbox[1] + 1)))
            objective_bonus = -50.0 if "objective" in o.affordances else 0.0
            tool_bonus = -20.0 if str(o.class_name).lower() in {"goal", "key", "button", "artifact", "teleporter", "switch"} else 0.0
            huge_penalty = 100.0 if o.area > max(256, (scene.width * scene.height) // 6) else 0.0
            return (objective_bonus + tool_bonus + huge_penalty + dist + 0.03 * area, -compact, area, o.object_id)

        return min(candidates, key=score)

    def record_decision(self, action: Any) -> None:
        name = _action_name(action)
        self.prev_action_name = name
        self.stats[name].last_used_step = self.step
        self.recent_actions.append(name)


# ---------------------------------------------------------------------------
# Planner.
# ---------------------------------------------------------------------------

class BudgetedReflectionPlanner:
    """Visible, logged planning-budget search.

    This is not hidden chain-of-thought. It is an explicit search budget used to
    rank action sequences from real frame state and learned action effects.

    Reward:
        + expected win proxy
        + target-distance improvement
        + remaining-budget bonus
        - repetition/stagnation penalties

    Budget:
        ARC3_REFLECT_BUDGET defaults to 10000 reflection units per game.
    """

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.enabled = os.environ.get("ARC3_REFLECT_ENABLED", "1").strip() != "0"
        self.total_budget = int(os.environ.get("ARC3_REFLECT_BUDGET", "10000"))
        self.remaining_budget = max(0, self.total_budget)
        self.per_step_budget = int(os.environ.get("ARC3_REFLECT_STEP_BUDGET", "240"))
        self.max_depth = int(os.environ.get("ARC3_REFLECT_DEPTH", "8"))
        self.max_branch = int(os.environ.get("ARC3_REFLECT_BRANCH", "6"))
        self.node_cost = int(os.environ.get("ARC3_REFLECT_NODE_COST", "7"))
        self.win_reward = float(os.environ.get("ARC3_REFLECT_WIN_REWARD", "10000"))
        self.remaining_reward_weight = float(os.environ.get("ARC3_REFLECT_REMAINING_REWARD", "250"))
        self.last_report: Dict[str, Any] = {}

    def choose(
        self,
        model: OnlineWorldModel,
        scene: Optional[Scene],
        actions: Sequence[Any],
    ) -> Optional[Tuple[Any, Dict[str, Any]]]:
        if not self.enabled:
            return None
        if self.remaining_budget <= 0:
            return None
        if scene is None or scene.actor is None or scene.target is None:
            self.last_report = {
                "enabled": True,
                "used": 0,
                "remaining": self.remaining_budget,
                "reason": "no_visible_actor_target",
            }
            return None

        simple_actions = [a for a in actions if not _is_complex_action(a)]
        if not simple_actions:
            return None

        under_tested = [a for a in simple_actions if model.stats[_action_name(a)].tries < 2]
        if under_tested:
            self.last_report = {
                "enabled": True,
                "used": 0,
                "remaining": self.remaining_budget,
                "reason": "awaiting_real_action_effect_tests",
                "under_tested": [_action_name(a) for a in under_tested],
            }
            return None

        start = scene.actor.centroid
        target = scene.target.centroid
        start_dist = _manhattan(start, target)

        # If actor is already on the target, use the least recently used action to
        # trigger completion/next-level effects, but spend minimal budget.
        if start_dist <= 0.25:
            action = min(simple_actions, key=lambda a: model.stats[_action_name(a)].tries)
            used = self._spend(3)
            reason = {
                "mode": "budgeted_reflection_terminal_nudge",
                "reflection_budget": {
                    "total": self.total_budget,
                    "used_this_step": used,
                    "remaining": self.remaining_budget,
                    "saved_reward": self._remaining_bonus(),
                },
                "start": start,
                "target": target,
                "start_distance": start_dist,
                "selected_action": _action_name(action),
            }
            return action, reason

        action_vectors = self._action_vectors(model, simple_actions)
        if not action_vectors:
            self.last_report = {
                "enabled": True,
                "used": 0,
                "remaining": self.remaining_budget,
                "reason": "no_action_vectors",
            }
            return None

        candidates = self._search(model, simple_actions, action_vectors, start, target, start_dist)

        if not candidates:
            self.last_report = {
                "enabled": True,
                "used": 0,
                "remaining": self.remaining_budget,
                "reason": "no_candidates",
            }
            return None

        candidates.sort(key=lambda c: c.score, reverse=True)
        best = candidates[0]
        by_name = {_action_name(a): a for a in simple_actions}
        action = by_name.get(best.first_action_name)
        if action is None:
            return None

        report_candidates = [
            {
                "first": c.first_action_name,
                "sequence": list(c.sequence),
                "score": round(c.score, 4),
                "predicted_distance": round(c.predicted_distance, 4),
                "token_cost": c.token_cost,
                "expected_reward": round(c.expected_reward, 4),
                "remaining_bonus": round(c.remaining_bonus, 4),
                "reason": c.reason,
            }
            for c in candidates[:8]
        ]

        reason = {
            "mode": "budgeted_reflection_plan",
            "reflection_budget": {
                "total": self.total_budget,
                "used_this_step": best.token_cost,
                "remaining": self.remaining_budget,
                "saved_reward": self._remaining_bonus(),
                "depth": self.max_depth,
                "branch": self.max_branch,
            },
            "actor": start,
            "target": target,
            "start_distance": start_dist,
            "selected_sequence": list(best.sequence),
            "selected_score": best.score,
            "candidate_plans": report_candidates,
            "known_vectors": {
                name: (round(vec[0], 4), round(vec[1], 4))
                for name, vec in sorted(action_vectors.items())
            },
        }
        return action, reason

    def _spend(self, amount: int) -> int:
        amount = max(0, int(amount))
        used = min(self.remaining_budget, amount)
        self.remaining_budget -= used
        return used

    def _remaining_bonus(self) -> float:
        if self.total_budget <= 0:
            return 0.0
        return self.remaining_reward_weight * (self.remaining_budget / self.total_budget)

    def _fallback_vector_from_action(self, action: Any) -> Optional[Point]:
        name = _action_name(action).upper()

        if "UP" in name:
            return (0.0, -1.0)
        if "DOWN" in name:
            return (0.0, 1.0)
        if "LEFT" in name:
            return (-1.0, 0.0)
        if "RIGHT" in name:
            return (1.0, 0.0)

        # ARC-AGI-3 games commonly expose ACTION1..ACTION5/ACTION7. The first
        # four are treated as a directional basis only until real deltas are
        # learned from frame transitions. This is a planning prior, not a mock.
        idx = _action_index(action)
        if idx == 1:
            return (0.0, -1.0)
        if idx == 2:
            return (0.0, 1.0)
        if idx == 3:
            return (-1.0, 0.0)
        if idx == 4:
            return (1.0, 0.0)
        if idx == 5:
            return (0.0, 0.0)
        if idx == 7:
            return (0.0, 0.0)
        return None

    def _action_vectors(self, model: OnlineWorldModel, actions: Sequence[Any]) -> Dict[str, Point]:
        vectors: Dict[str, Point] = {}
        for action in actions:
            name = _action_name(action)
            stat = model.stats[name]
            learned = stat.vector()
            if learned is not None:
                vectors[name] = learned
                continue

            # After real frame testing, do not hallucinate movement vectors for
            # ACTION1/ACTION2/ACTION3/ACTION4.  The tr87 run proved generic
            # fallback vectors can cause a 200-step ACTION3 spiral.  Reflection
            # now requires observed real deltas before planning.
            if stat.tries >= 1:
                continue

            # Keep literal named directions usable before testing if a future
            # environment exposes names like UP/DOWN/LEFT/RIGHT.
            if _looks_like_directional_action(name):
                fallback = self._fallback_vector_from_action(action)
                if fallback is not None:
                    vectors[name] = fallback
        return vectors

    def _search(
        self,
        model: OnlineWorldModel,
        actions: Sequence[Any],
        vectors: Dict[str, Point],
        start: Point,
        target: Point,
        start_dist: float,
    ) -> List[ReflectionCandidate]:
        recent = Counter(model.recent_actions)
        ordered_actions = sorted(
            actions,
            key=lambda a: (
                recent[_action_name(a)],
                model.stats[_action_name(a)].tries,
                _action_value(a),
            ),
        )[: self.max_branch]

        candidates: List[ReflectionCandidate] = []
        frontier: List[Tuple[Point, Tuple[str, ...], float, float]] = [(start, tuple(), start_dist, 0.0)]

        total_spent = 0
        spend_cap = max(1, min(self.remaining_budget, self.per_step_budget))
        max_nodes = max(1, spend_cap // max(1, self.node_cost))

        for depth in range(1, self.max_depth + 1):
            next_frontier: List[Tuple[Point, Tuple[str, ...], float, float]] = []
            for pos, seq, prev_dist, seq_penalty in frontier:
                for action in ordered_actions:
                    if total_spent >= max_nodes * self.node_cost:
                        break

                    name = _action_name(action)
                    vec = vectors.get(name)
                    if vec is None:
                        continue

                    total_spent += self.node_cost
                    nx = pos[0] + vec[0]
                    ny = pos[1] + vec[1]
                    new_pos = (nx, ny)
                    dist = _manhattan(new_pos, target)

                    progress = start_dist - dist
                    immediate_progress = prev_dist - dist
                    repeated = 1 if seq and seq[-1] == name else 0
                    recent_penalty = 0.15 * recent[name]
                    no_move_penalty = 0.30 if abs(vec[0]) + abs(vec[1]) <= 0.01 else 0.0
                    loop_penalty = 0.20 * repeated + recent_penalty + no_move_penalty + seq_penalty

                    win_proxy = self.win_reward if dist <= 0.50 else 0.0
                    expected_reward = win_proxy + (125.0 * progress) + (20.0 * immediate_progress)
                    remaining_after_node = max(0, self.remaining_budget - total_spent)
                    remaining_bonus = (
                        self.remaining_reward_weight * (remaining_after_node / self.total_budget)
                        if self.total_budget > 0
                        else 0.0
                    )
                    score = expected_reward + remaining_bonus - loop_penalty - (0.05 * depth)

                    new_seq = seq + (name,)
                    candidates.append(
                        ReflectionCandidate(
                            first_action_name=new_seq[0],
                            sequence=new_seq,
                            score=float(score),
                            predicted_position=new_pos,
                            predicted_distance=float(dist),
                            token_cost=int(total_spent),
                            expected_reward=float(expected_reward),
                            remaining_bonus=float(remaining_bonus),
                            reason="target_reached" if dist <= 0.50 else "distance_reward_search",
                        )
                    )

                    # Keep expanding only plausible branches.
                    if dist <= prev_dist + 1.25:
                        next_frontier.append((new_pos, new_seq, dist, loop_penalty))

                if total_spent >= max_nodes * self.node_cost:
                    break

            if not next_frontier:
                break

            next_frontier.sort(key=lambda item: item[2] + 0.1 * len(item[1]))
            frontier = next_frontier[: max(4, self.max_branch * 2)]

            # If there are target-reaching candidates, stop early to preserve budget.
            if any(c.predicted_distance <= 0.50 for c in candidates):
                break

        spent = self._spend(total_spent)
        # Adjust all candidates to real spent amount for this decision.
        adjusted: List[ReflectionCandidate] = []
        for c in candidates:
            adjusted.append(
                ReflectionCandidate(
                    first_action_name=c.first_action_name,
                    sequence=c.sequence,
                    score=c.score,
                    predicted_position=c.predicted_position,
                    predicted_distance=c.predicted_distance,
                    token_cost=spent,
                    expected_reward=c.expected_reward,
                    remaining_bonus=self._remaining_bonus(),
                    reason=c.reason,
                )
            )
        return adjusted


class ExploreVerifyPlan:
    """Action selector: explores first, verifies effects, then plans by learned vectors."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.opening_script_index = 0

    def choose(
        self,
        model: OnlineWorldModel,
        scene: Optional[Scene],
        actions: Sequence[Any],
        reset_action: Optional[Any],
    ) -> Tuple[Any, Dict[str, Any]]:
        simple_actions = [a for a in actions if not _is_complex_action(a)]
        complex_actions = [a for a in actions if _is_complex_action(a)]

        if not actions:
            if reset_action is not None:
                return reset_action, {"mode": "fallback_reset", "reason": "no candidate actions available"}
            raise RuntimeError("No GameAction candidates are available")

        # If completely blind, rotate through candidate actions by least use.
        if scene is None:
            action = self._least_used_action(model, simple_actions or actions)
            return action, {
                "mode": "blind_explore",
                "reason": "no extractable grid in frame",
                "tries": model.stats[_action_name(action)].tries,
            }

        actor = scene.actor
        target = scene.target

        # Periodically test complex coordinate action against target if available.
        if complex_actions and target is not None:
            should_click_probe = (
                model.step == 1
                or (actor is None and model.step % 5 == 0)
                or (model.stagnation >= 8 and model.step % 3 == 0)
                or (model.step > 20 and model.step % 13 == 0 and self._complex_actions_have_signal(model, complex_actions))
            )
            if should_click_probe:
                action = self._least_used_action(model, complex_actions)
                self._attach_click_target(action, scene, target.centroid)
                return action, {
                    "mode": "complex_target_probe",
                    "target_object": target.object_id,
                    "target_class": target.class_name,
                    "target_centroid": target.centroid,
                    "stagnation": model.stagnation,
                }

        # Prefer real measured progress before vector geometry.  This prevents
        # the planner from repeatedly using a movement-looking action unless it
        # has actually reduced actor-to-target distance in this game.
        if actor is not None and target is not None:
            progress_choice = self._best_progress_action(model, simple_actions or actions)
            if progress_choice is not None:
                action, score = progress_choice
                stat = model.stats[_action_name(action)]
                return action, {
                    "mode": "verified_progress_plan",
                    "actor": actor.centroid,
                    "target": target.centroid,
                    "target_class": target.class_name,
                    "score": score,
                    "action_stats": {
                        "tries": stat.tries,
                        "changed": stat.changed,
                        "avg_progress": stat.avg_progress(),
                        "positive_progress": stat.positive_progress,
                        "negative_progress": stat.negative_progress,
                    },
                }

        # Plan toward target using learned action vectors.
        if actor is not None and target is not None:
            planned = self._best_vector_action(model, simple_actions or actions, actor.centroid, target.centroid)
            if planned is not None:
                action, score = planned
                return action, {
                    "mode": "learned_vector_plan",
                    "actor": actor.centroid,
                    "target": target.centroid,
                    "target_class": target.class_name,
                    "score": score,
                    "known_vectors": {
                        name: model.stats[name].vector()
                        for name in sorted(model.stats)
                        if model.stats[name].vector() is not None
                    },
                }

        # Verify all simple actions enough to learn their effect.
        under_tested = [
            a for a in (simple_actions or actions)
            if model.stats[_action_name(a)].tries < 2
        ]
        if under_tested:
            action = self._least_used_action(model, under_tested)
            return action, {
                "mode": "verify_action_effect",
                "action": _action_name(action),
                "tries": model.stats[_action_name(action)].tries,
            }

        # Break loops by trying a stale action.
        if model.stagnation >= 6:
            pool = simple_actions or actions
            action = max(pool, key=lambda a: model.step - model.stats[_action_name(a)].last_used_step)
            return action, {
                "mode": "stagnation_escape",
                "stagnation": model.stagnation,
                "action": _action_name(action),
            }

        # Intrinsic exploration: prefer actions that historically changed state.
        pool = simple_actions or actions
        if all(model.stats[_action_name(a)].changed == 0 for a in pool):
            action = max(
                pool,
                key=lambda a: (
                    model.step - model.stats[_action_name(a)].last_used_step,
                    -model.stats[_action_name(a)].tries,
                    -_action_value(a),
                ),
            )
            return action, {
                "mode": "effectless_round_robin",
                "reason": "no_available_action_has_observed_state_delta",
                "stagnation": model.stagnation,
                "tries": { _action_name(a): model.stats[_action_name(a)].tries for a in pool },
            }

        scored: List[Tuple[float, Any]] = []
        recent_counts = Counter(model.recent_actions)
        for a in pool:
            name = _action_name(a)
            stat = model.stats[name]
            score = 0.0
            score += 1.20 * stat.success_rate()
            score += 0.15 / (1.0 + stat.tries)
            score += 0.01 * min(25, model.step - stat.last_used_step)
            score -= 0.12 * recent_counts[name]
            if stat.tries >= 2 and stat.changed == 0:
                score -= 0.60
            score += self.rng.random() * 0.02
            scored.append((score, a))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1], {
            "mode": "intrinsic_explore",
            "score": scored[0][0],
            "top": [(round(s, 4), _action_name(a)) for s, a in scored[:4]],
        }

    def _least_used_action(self, model: OnlineWorldModel, actions: Sequence[Any]) -> Any:
        return min(
            actions,
            key=lambda a: (
                model.stats[_action_name(a)].tries,
                -1 * (model.step - model.stats[_action_name(a)].last_used_step),
                _action_value(a),
            ),
        )

    def _complex_actions_have_signal(self, model: OnlineWorldModel, actions: Sequence[Any]) -> bool:
        for action in actions:
            stat = model.stats[_action_name(action)]
            if stat.tries > 0 and (stat.changed > 0 or stat.wins > 0):
                return True
        return False

    def _best_progress_action(
        self,
        model: OnlineWorldModel,
        actions: Sequence[Any],
    ) -> Optional[Tuple[Any, float]]:
        candidates: List[Tuple[float, Any]] = []
        recent_counts = Counter(model.recent_actions)

        for action in actions:
            name = _action_name(action)
            stat = model.stats[name]
            if stat.tries < 2:
                continue
            if stat.positive_progress <= 0:
                continue

            score = 0.0
            score += 5.0 * stat.avg_progress()
            score += 1.5 * stat.progress_confidence()
            score += 0.5 * stat.success_rate()
            score -= 0.35 * stat.negative_progress
            score -= 0.25 * recent_counts[name]
            score += 0.01 * min(30, model.step - stat.last_used_step)

            if score > 0.01:
                candidates.append((score, action))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1], candidates[0][0]

    def _best_vector_action(
        self,
        model: OnlineWorldModel,
        actions: Sequence[Any],
        actor: Point,
        target: Point,
    ) -> Optional[Tuple[Any, float]]:
        desired = (target[0] - actor[0], target[1] - actor[1])
        desired_len = math.sqrt(desired[0] * desired[0] + desired[1] * desired[1])
        if desired_len <= 1e-9:
            return None

        recent_counts = Counter(model.recent_actions)
        candidates: List[Tuple[float, Any]] = []

        for action in actions:
            name = _action_name(action)
            stat = model.stats[name]
            vec = stat.vector()

            if vec is None:
                # No generic ACTION# fallback after real testing.  A no-change
                # action is not a movement primitive.  This prevents long
                # ACTION3 spirals when role inference says "target is left"
                # but the environment did not confirm ACTION3 moves left.
                if stat.tries > 0:
                    continue
                if _looks_like_directional_action(name):
                    vec = self._fallback_vector_from_name(name)
                if vec is None:
                    continue

            vx, vy = vec
            vlen = math.sqrt(vx * vx + vy * vy)
            if vlen <= 1e-9:
                continue

            alignment = (vx * desired[0] + vy * desired[1]) / (vlen * desired_len)
            progress = _manhattan(actor, target) - _manhattan((actor[0] + vx, actor[1] + vy), target)
            score = alignment + 0.30 * progress + 0.20 * stat.success_rate()
            score -= 0.10 * recent_counts[name]
            score += self.rng.random() * 0.01
            candidates.append((score, action))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        if candidates[0][0] <= -0.25:
            return None
        best_score, best_action = candidates[0]
        return best_action, best_score

    def _fallback_vector_from_name(self, name: str) -> Optional[Point]:
        upper = name.upper()
        if "UP" in upper:
            return (0.0, -1.0)
        if "DOWN" in upper:
            return (0.0, 1.0)
        if "LEFT" in upper:
            return (-1.0, 0.0)
        if "RIGHT" in upper:
            return (1.0, 0.0)

        # Conservative generic mapping for common six-action controllers.
        # It is only used after actual testing failed to estimate a vector.
        mapping = {
            "ACTION1": (0.0, -1.0),
            "ACTION2": (0.0, 1.0),
            "ACTION3": (-1.0, 0.0),
            "ACTION4": (1.0, 0.0),
        }
        return mapping.get(upper)

    def _attach_click_target(self, action: Any, scene: Scene, centroid: Point) -> None:
        # Official sample describes ACTION6 coords on a 64x64 grid.
        # Scale from extracted grid coordinates to the action coordinate plane.
        x, y = centroid
        if scene.width <= 1:
            sx = 0
        else:
            sx = x * 63.0 / (scene.width - 1)
        if scene.height <= 1:
            sy = 0
        else:
            sy = y * 63.0 / (scene.height - 1)
        _set_action_data(action, {"x": _clamp_int(sx, 0, 63), "y": _clamp_int(sy, 0, 63)})


# ---------------------------------------------------------------------------
# Optional lightweight logging.
# ---------------------------------------------------------------------------

class RunLogger:
    def __init__(self, game_id: str) -> None:
        self.enabled = os.environ.get("ARC3_LOG", "0").strip() == "1"
        self.path: Optional[str] = None
        if self.enabled:
            base = os.environ.get("ARC3_LOG_DIR", "/tmp/arc3_glyph_agent_runs")
            try:
                os.makedirs(base, exist_ok=True)
                safe_game = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in game_id)[:80]
                self.path = os.path.join(base, f"{safe_game}_{int(time.time())}.jsonl")
            except Exception:
                self.enabled = False
                self.path = None

    def write(self, event: Dict[str, Any]) -> None:
        if not self.enabled or not self.path:
            return
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_json_safe(event), ensure_ascii=False, sort_keys=True) + "\n")
        except Exception:
            self.enabled = False


class FrameProbe:
    """Real-runtime frame inspector.

    Enabled only with ARC3_FRAME_PROBE=1. It writes compact JSONL summaries of
    the actual latest_frame object and the extractor result. No simulation and
    no fake game data.
    """

    def __init__(self, game_id: str) -> None:
        self.enabled = os.environ.get("ARC3_FRAME_PROBE", "0").strip() == "1"
        self.max_frames = int(os.environ.get("ARC3_FRAME_PROBE_N", "8"))
        self.count = 0
        self.path: Optional[str] = None
        if self.enabled:
            base = os.environ.get("ARC3_LOG_DIR", "/tmp/arc3_glyph_agent_runs")
            try:
                os.makedirs(base, exist_ok=True)
                safe_game = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(game_id))[:80]
                self.path = os.path.join(base, f"frame_probe_{safe_game}_{int(time.time())}.jsonl")
            except Exception:
                self.enabled = False
                self.path = None

    def write(self, frame: Any, grid: Optional[Grid], scene: Optional[Scene], state_name: str, step: int) -> None:
        if not self.enabled or not self.path or self.count >= self.max_frames:
            return
        self.count += 1
        event = {
            "kind": "frame_probe",
            "step": step,
            "state": state_name,
            "frame_type": type(frame).__name__,
            "frame_module": type(frame).__module__,
            "frame_summary": self._summarize_object(frame, depth=0),
            "grid_summary": self._summarize_grid(grid),
            "scene_summary": {
                "visible": scene is not None,
                "hash": scene.grid_hash if scene is not None else None,
                "size": [scene.width, scene.height] if scene is not None else None,
                "objects": len(scene.objects) if scene is not None else 0,
                "actor": scene.actor.class_name if scene is not None and scene.actor is not None else None,
                "actor_id": scene.actor.object_id if scene is not None and scene.actor is not None else None,
                "actor_class_id": scene.actor.class_id if scene is not None and scene.actor is not None else None,
                "actor_area": scene.actor.area if scene is not None and scene.actor is not None else None,
                "actor_centroid": scene.actor.centroid if scene is not None and scene.actor is not None else None,
                "target": scene.target.class_name if scene is not None and scene.target is not None else None,
                "target_id": scene.target.object_id if scene is not None and scene.target is not None else None,
                "target_class_id": scene.target.class_id if scene is not None and scene.target is not None else None,
                "target_area": scene.target.area if scene is not None and scene.target is not None else None,
                "target_centroid": scene.target.centroid if scene is not None and scene.target is not None else None,
            },
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_json_safe(event, limit=200), ensure_ascii=False, sort_keys=True) + "\n")
        except Exception:
            self.enabled = False

    def _summarize_grid(self, grid: Optional[Grid]) -> Dict[str, Any]:
        if grid is None:
            return {"present": False}
        if not grid or not grid[0]:
            return {"present": True, "empty": True}
        counts = Counter(v for row in grid for v in row)
        return {
            "present": True,
            "height": len(grid),
            "width": len(grid[0]),
            "hash": _stable_hash_grid(grid),
            "values": dict(sorted((int(k), int(v)) for k, v in counts.items())),
            "preview": ["".join(str(int(v) % 10) for v in row[:80]) for row in grid[:12]],
        }

    def _summarize_object(self, obj: Any, depth: int) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "type": type(obj).__name__,
            "module": type(obj).__module__,
        }

        shape = _safe_getattr(obj, "shape", None)
        if shape is not None:
            out["shape"] = str(shape)

        if isinstance(obj, dict):
            out["keys"] = [str(k) for k in list(obj.keys())[:40]]
            if depth < 2:
                out["items"] = {
                    str(k): self._summarize_value(v, depth + 1)
                    for k, v in list(obj.items())[:20]
                }
            return out

        if isinstance(obj, (list, tuple)):
            out["len"] = len(obj)
            if obj:
                out["first"] = self._summarize_value(obj[0], depth + 1)
            return out

        # Dataclass/pydantic/dynamic frame: inspect public attrs.
        attrs: List[str] = []
        try:
            attrs = [
                name for name in dir(obj)
                if not name.startswith("_")
                and name not in ("copy", "dict", "json", "model_dump", "schema", "schema_json")
            ]
        except Exception:
            attrs = []

        out["attrs"] = attrs[:80]
        if depth < 2:
            values: Dict[str, Any] = {}
            for name in attrs[:40]:
                try:
                    value = getattr(obj, name)
                except Exception as exc:
                    values[name] = {"error": str(exc)[:120]}
                    continue
                if callable(value):
                    values[name] = {"callable": True}
                else:
                    values[name] = self._summarize_value(value, depth + 1)
            out["values"] = values

        try:
            out["repr"] = repr(obj)[:300]
        except Exception:
            pass
        return out

    def _summarize_value(self, value: Any, depth: int) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value if not isinstance(value, str) else value[:300]

        shape = _safe_getattr(value, "shape", None)
        dtype = _safe_getattr(value, "dtype", None)
        if shape is not None:
            return {
                "type": type(value).__name__,
                "shape": str(shape),
                "dtype": str(dtype) if dtype is not None else None,
            }

        if isinstance(value, dict):
            return self._summarize_object(value, depth)

        if isinstance(value, (list, tuple)):
            summary: Dict[str, Any] = {"type": type(value).__name__, "len": len(value)}
            if value:
                summary["first"] = self._summarize_value(value[0], depth + 1)
            return summary

        if depth < 2:
            return self._summarize_object(value, depth)

        try:
            return {"type": type(value).__name__, "repr": repr(value)[:180]}
        except Exception:
            return {"type": type(value).__name__}


# ---------------------------------------------------------------------------
# ARC-AGI-3 agent.
# ---------------------------------------------------------------------------

class MyAgent(Agent):
    """Glyph-flood Braille symbolic ARC-AGI-3 agent."""

    MAX_ACTIONS = int(os.environ.get("ARC3_MAX_ACTIONS", "300"))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        gid = str(_safe_getattr(self, "game_id", "unknown-game"))
        seed = int(os.environ.get("ARC3_SEED", "918"))
        seed ^= hash(gid) & 0xFFFFFFFF
        self.rng = random.Random(seed)
        self.extractor = ObservationExtractor()
        self.vision = GlyphFloodVision()
        self.model = OnlineWorldModel()
        self.route_planner = BVSNavigationPlanner(DEFAULT_CLASS_SPECS)
        self.reflection_planner = BudgetedReflectionPlanner(self.rng)
        self.planner = ExploreVerifyPlan(self.rng)
        self.logger = RunLogger(gid)
        self.frame_probe = FrameProbe(gid)
        self.action_counter = 0
        self._last_decision: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        base = "GlyphFloodBraille"
        gid = str(_safe_getattr(self, "game_id", "game")).split("-")[0]
        return f"{base}.{gid}.{self.MAX_ACTIONS}"

    def is_done(self, frames: List[FrameData], latest_frame: FrameData) -> bool:
        state = _state_name(_safe_getattr(latest_frame, "state", None))
        if state == "WIN":
            return True
        if self.action_counter >= self.MAX_ACTIONS:
            return True
        return False

    def choose_action(self, frames: List[FrameData], latest_frame: FrameData) -> GameAction:
        state = _state_name(_safe_getattr(latest_frame, "state", None))

        reset_action = self._reset_action()
        if state in ("NOT_PLAYED", "GAME_OVER"):
            action = reset_action if reset_action is not None else self._first_candidate_action()
            _set_reasoning(action, {"agent": self.name, "mode": "reset", "state": state})
            self.model.record_decision(action)
            self.action_counter += 1
            return action

        grid = self.extractor.extract(latest_frame)
        scene = self.vision.analyze(grid)
        self.model.update_before_decision(scene, state)
        self.frame_probe.write(latest_frame, grid, scene, state, self.action_counter)

        candidate_actions = self._candidate_actions(latest_frame)

        routed = self.route_planner.choose(grid, scene, self.model, candidate_actions)
        if routed is not None:
            action, reason = routed
        else:
            reflected = self.reflection_planner.choose(self.model, scene, candidate_actions)
            if reflected is not None:
                action, reason = reflected
            else:
                action, reason = self.planner.choose(self.model, scene, candidate_actions, reset_action)
            reason["bvs_astar_diagnostic"] = self.route_planner.last_diagnostic
        self.action_counter += 1

        reason.update(
            {
                "agent": self.name,
                "step": self.action_counter,
                "game_id": str(_safe_getattr(self, "game_id", "unknown")),
                "state": state,
                "scene": self._scene_summary(scene),
                "motion_role": self.model.last_motion_role_reason,
                "available_actions": [_action_name(a) for a in candidate_actions],
                "selected_action": _action_name(action),
            }
        )

        _set_reasoning(action, reason)
        self.model.record_decision(action)
        self._last_decision = reason
        self.logger.write(reason)
        return action

    def _candidate_actions(self, latest_frame: Optional[Any] = None) -> List[Any]:
        try:
            actions = [a for a in GameAction if _action_name(a) != "RESET"]
        except Exception:
            actions = []
            for name in ("ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7", "UP", "DOWN", "LEFT", "RIGHT", "WAIT"):
                a = _safe_getattr(GameAction, name, None)
                if a is not None and _action_name(a) != "RESET":
                    actions.append(a)

        available_raw = _safe_getattr(latest_frame, "available_actions", None) if latest_frame is not None else None
        allowed_values: Optional[set[int]] = None
        if isinstance(available_raw, (list, tuple, set)) and available_raw:
            allowed_values = set()
            for item in available_raw:
                try:
                    allowed_values.add(int(item))
                except Exception:
                    try:
                        allowed_values.add(int(getattr(item, "value")))
                    except Exception:
                        pass

        if allowed_values:
            filtered = [a for a in actions if _action_value(a) in allowed_values]
            if filtered:
                actions = filtered

        # Stable order helps reproducible exploration.
        actions = sorted(actions, key=lambda a: (_is_complex_action(a), _action_value(a), _action_name(a)))
        return actions

    def _reset_action(self) -> Optional[Any]:
        return _safe_getattr(GameAction, "RESET", None)

    def _first_candidate_action(self) -> Any:
        actions = self._candidate_actions()
        if actions:
            return actions[0]
        reset = self._reset_action()
        if reset is not None:
            return reset
        raise RuntimeError("No GameAction values found")

    def _scene_summary(self, scene: Optional[Scene]) -> Dict[str, Any]:
        if scene is None:
            return {"visible": False}

        actor_summary: Optional[Dict[str, Any]] = None
        if scene.actor is not None:
            actor_summary = {
                "id": scene.actor.object_id,
                "class": scene.actor.class_name,
                "centroid": scene.actor.centroid,
                "braille": scene.actor.braille,
            }

        target_summary: Optional[Dict[str, Any]] = None
        if scene.target is not None:
            target_summary = {
                "id": scene.target.object_id,
                "class": scene.target.class_name,
                "centroid": scene.target.centroid,
                "braille": scene.target.braille,
            }

        return {
            "visible": True,
            "size": [scene.width, scene.height],
            "hash": scene.grid_hash,
            "objects": len(scene.objects),
            "class_counts": scene.class_counts,
            "actor": actor_summary,
            "target": target_summary,
            "braille_preview": scene.braille_map[:500],
        }
