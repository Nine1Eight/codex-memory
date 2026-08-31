from __future__ import annotations

import json
import math
import os
import random
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from arcengine import FrameData, GameAction, GameState

from .agent import Agent


Grid = list[list[int]]
Coord = tuple[int, int]


@dataclass
class ActionStats:
    pulls: int = 0
    reward_sum: float = 0.0
    reward_sq_sum: float = 0.0
    last_reward: float = 0.0
    no_change_streak: int = 0

    @property
    def mean(self) -> float:
        return self.reward_sum / self.pulls if self.pulls else 0.0

    @property
    def variance(self) -> float:
        if self.pulls <= 1:
            return 0.0
        mean = self.mean
        return max(0.0, self.reward_sq_sum / self.pulls - mean * mean)

    def update(self, reward: float, changed: bool) -> None:
        self.pulls += 1
        self.reward_sum += reward
        self.reward_sq_sum += reward * reward
        self.last_reward = reward
        if changed:
            self.no_change_streak = 0
        else:
            self.no_change_streak += 1


@dataclass
class FrameFeatures:
    fingerprint: str
    width: int
    height: int
    histogram: dict[int, int]
    background: int
    occupied: int
    bbox: Optional[tuple[int, int, int, int]]
    components: list[dict[str, Any]] = field(default_factory=list)


class Nine18WorldModel(Agent):
    """
    General ARC-AGI-3 exploratory agent.

    The agent does not contain game-specific rules. It builds an online transition
    model from observations, scores action effects by level progress, frame
    novelty, and reversible/irreversible state changes, then uses a bounded
    UCB-style policy with coordinate targeting for complex actions.
    """

    MAX_ACTIONS = int(os.getenv("NINE18_MAX_ACTIONS", "180"))
    MEMORY_DIR = Path(os.getenv("NINE18_MEMORY_DIR", "nine18_memory"))
    VERSION = "nine18-world-model-v1.0.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        seed_material = f"{self.game_id}:{self.card_id}:{self.VERSION}"
        self.seed = abs(hash(seed_material)) % (2**32)
        self.rng = random.Random(self.seed)
        self.stats: dict[int, ActionStats] = {}
        self.visited: Counter[str] = Counter()
        self.transition_counts: Counter[tuple[str, int, str]] = Counter()
        self.last_learned_frame_count = 0
        self.pending_action_id: Optional[int] = None
        self.last_grid: Optional[Grid] = None
        self.last_features: Optional[FrameFeatures] = None
        self.coordinate_queue: deque[Coord] = deque()
        self.recent_fingerprints: deque[str] = deque(maxlen=16)
        self.recent_actions: deque[int] = deque(maxlen=16)
        self.feature_log_enabled = os.getenv("NINE18_DISABLE_MEMORY_LOG", "0") not in {"1", "true", "TRUE"}
        if self.feature_log_enabled:
            self.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            self.memory_path = self.MEMORY_DIR / f"{self.game_id}.jsonl"
        else:
            self.memory_path = None

    @property
    def name(self) -> str:
        return f"{super().name}.{self.VERSION}.{self.MAX_ACTIONS}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        state = getattr(latest_frame, "state", GameState.NOT_PLAYED)
        return state is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        self._learn_from_new_frames(frames)

        state = getattr(latest_frame, "state", GameState.NOT_PLAYED)
        if state in {GameState.NOT_PLAYED, GameState.GAME_OVER}:
            action = GameAction.RESET
            self._prepare_action(action, latest_frame, reason={"mode": "reset", "state": str(state)})
            self.pending_action_id = int(action.value)
            return action

        available = self._available_actions(latest_frame)
        if not available:
            action = GameAction.RESET
            self._prepare_action(action, latest_frame, reason={"mode": "fallback_reset", "available": 0})
            self.pending_action_id = int(action.value)
            return action

        non_reset = [a for a in available if a is not GameAction.RESET]
        candidates = non_reset if non_reset else available

        latest_grid = self._to_grid(getattr(latest_frame, "frame", []))
        latest_features = self._features(latest_grid)
        self._refresh_coordinate_queue(latest_grid, latest_features)

        action = self._select_action(candidates, latest_features)
        self._prepare_action(
            action,
            latest_frame,
            reason={
                "agent": self.VERSION,
                "mode": "online_world_model_ucb",
                "step": self.action_counter,
                "fingerprint": latest_features.fingerprint,
                "levels_completed": self._levels_completed(latest_frame),
                "known_states": len(self.visited),
                "available_actions": [int(a.value) for a in available],
                "selected_action": int(action.value),
            },
        )
        self.pending_action_id = int(action.value)
        return action

    def _available_actions(self, frame: FrameData) -> list[GameAction]:
        raw_actions = getattr(frame, "available_actions", None) or []
        normalized: list[GameAction] = []
        for raw in raw_actions:
            action = self._coerce_action(raw)
            if action is not None and action not in normalized:
                normalized.append(action)
        if normalized:
            return normalized
        return [a for a in GameAction]

    def _coerce_action(self, raw: Any) -> Optional[GameAction]:
        if isinstance(raw, GameAction):
            return raw
        if isinstance(raw, int):
            try:
                return GameAction.from_id(raw)
            except Exception:
                return None
        if isinstance(raw, str):
            token = raw.strip()
            if token.isdigit():
                try:
                    return GameAction.from_id(int(token))
                except Exception:
                    return None
            try:
                return GameAction.from_name(token)
            except Exception:
                return None
        value = getattr(raw, "value", None)
        if isinstance(value, int):
            try:
                return GameAction.from_id(value)
            except Exception:
                return None
        name = getattr(raw, "name", None)
        if isinstance(name, str):
            try:
                return GameAction.from_name(name)
            except Exception:
                return None
        return None

    def _select_action(self, actions: list[GameAction], features: FrameFeatures) -> GameAction:
        for action in actions:
            stats = self.stats.get(int(action.value))
            if stats is None or stats.pulls == 0:
                return action

        total = max(1, sum(self.stats.get(int(a.value), ActionStats()).pulls for a in actions))
        loop_penalty_ids = set(self.recent_actions) if self._appears_looping(features.fingerprint) else set()
        best_score = -1.0e18
        best_action = actions[0]
        for action in actions:
            action_id = int(action.value)
            stats = self.stats.setdefault(action_id, ActionStats())
            exploration = math.sqrt(2.0 * math.log(total + 1.0) / max(1, stats.pulls))
            novelty_bias = 0.15 / (1.0 + self._projected_repeat_pressure(features.fingerprint, action_id))
            variance_bonus = 0.05 * math.sqrt(stats.variance)
            no_change_penalty = 0.18 * min(5, stats.no_change_streak)
            loop_penalty = 0.35 if action_id in loop_penalty_ids else 0.0
            complex_bias = 0.08 if action.is_complex() and self.coordinate_queue else 0.0
            score = stats.mean + exploration + novelty_bias + variance_bonus + complex_bias - no_change_penalty - loop_penalty
            if score > best_score:
                best_score = score
                best_action = action
        return best_action

    def _projected_repeat_pressure(self, fingerprint: str, action_id: int) -> int:
        total = 0
        for (src, aid, _dst), count in self.transition_counts.items():
            if src == fingerprint and aid == action_id:
                total += count
        return total

    def _appears_looping(self, fingerprint: str) -> bool:
        if len(self.recent_fingerprints) < self.recent_fingerprints.maxlen:
            return False
        counts = Counter(self.recent_fingerprints)
        return counts[fingerprint] >= 4 or len(counts) <= 4

    def _prepare_action(self, action: GameAction, frame: FrameData, reason: dict[str, Any]) -> None:
        if action.is_complex():
            x, y = self._next_coordinate(frame)
            action.set_data({"game_id": self.game_id, "x": x, "y": y})
            reason = dict(reason)
            reason["target"] = {"x": x, "y": y}
            action.reasoning = reason
        else:
            try:
                action.set_data({"game_id": self.game_id})
            except Exception:
                action.set_data({})
            action.reasoning = reason

    def _next_coordinate(self, frame: FrameData) -> Coord:
        grid = self._to_grid(getattr(frame, "frame", []))
        height = len(grid) or 64
        width = len(grid[0]) if grid and grid[0] else 64
        if not self.coordinate_queue:
            self._refresh_coordinate_queue(grid, self._features(grid))
        if self.coordinate_queue:
            x, y = self.coordinate_queue.popleft()
            return max(0, min(63, x)), max(0, min(63, y))
        idx = self.action_counter + 1
        x = int(((idx * 0.6180339887498949 + (self.seed % 997) / 997.0) % 1.0) * max(1, width))
        y = int(((idx * 0.4142135623730950 + (self.seed % 991) / 991.0) % 1.0) * max(1, height))
        return max(0, min(63, x)), max(0, min(63, y))

    def _refresh_coordinate_queue(self, grid: Grid, features: FrameFeatures) -> None:
        if self.coordinate_queue:
            return
        height = len(grid)
        width = len(grid[0]) if height else 0
        if width <= 0 or height <= 0:
            self.coordinate_queue.extend([(32, 32), (16, 16), (48, 16), (16, 48), (48, 48)])
            return

        points: list[Coord] = []
        if features.bbox is not None:
            x0, y0, x1, y1 = features.bbox
            points.extend(
                [
                    ((x0 + x1) // 2, (y0 + y1) // 2),
                    (x0, y0),
                    (x1, y0),
                    (x0, y1),
                    (x1, y1),
                ]
            )
        for comp in features.components[:8]:
            cx = int(comp.get("cx", width // 2))
            cy = int(comp.get("cy", height // 2))
            points.append((cx, cy))

        if self.last_grid is not None:
            changed = self._changed_cells(self.last_grid, grid, limit=24)
            points.extend(changed)

        center_points = [
            (width // 2, height // 2),
            (width // 4, height // 4),
            (3 * width // 4, height // 4),
            (width // 4, 3 * height // 4),
            (3 * width // 4, 3 * height // 4),
        ]
        points.extend(center_points)

        unique: list[Coord] = []
        seen: set[Coord] = set()
        for x, y in points:
            px = max(0, min(width - 1, x))
            py = max(0, min(height - 1, y))
            coord = (max(0, min(63, px)), max(0, min(63, py)))
            if coord not in seen:
                seen.add(coord)
                unique.append(coord)

        while len(unique) < 16:
            idx = len(unique) + self.action_counter + 1
            x = int(((idx * 0.6180339887498949 + (self.seed % 997) / 997.0) % 1.0) * width)
            y = int(((idx * 0.4142135623730950 + (self.seed % 991) / 991.0) % 1.0) * height)
            coord = (max(0, min(63, x)), max(0, min(63, y)))
            if coord not in seen:
                seen.add(coord)
                unique.append(coord)
        self.coordinate_queue.extend(unique)

    def _learn_from_new_frames(self, frames: list[FrameData]) -> None:
        if not frames:
            return
        start = max(1, self.last_learned_frame_count)
        for idx in range(start, len(frames)):
            prev = frames[idx - 1]
            curr = frames[idx]
            prev_grid = self._to_grid(getattr(prev, "frame", []))
            curr_grid = self._to_grid(getattr(curr, "frame", []))
            prev_features = self._features(prev_grid)
            curr_features = self._features(curr_grid)
            action_id = self._frame_action_id(curr, fallback=self.pending_action_id)
            reward = self._transition_reward(prev, curr, prev_features, curr_features)
            changed = prev_features.fingerprint != curr_features.fingerprint

            if action_id is not None:
                stats = self.stats.setdefault(action_id, ActionStats())
                stats.update(reward, changed)
                self.transition_counts[(prev_features.fingerprint, action_id, curr_features.fingerprint)] += 1

            self.visited[curr_features.fingerprint] += 1
            self.recent_fingerprints.append(curr_features.fingerprint)
            if action_id is not None:
                self.recent_actions.append(action_id)
            self.last_grid = curr_grid
            self.last_features = curr_features
            self._log_transition(prev, curr, action_id, reward, changed, curr_features)
        self.last_learned_frame_count = len(frames)

    def _frame_action_id(self, frame: FrameData, fallback: Optional[int]) -> Optional[int]:
        action_input = getattr(frame, "action_input", None)
        raw_id = getattr(action_input, "id", None)
        if isinstance(raw_id, GameAction):
            return int(raw_id.value)
        if isinstance(raw_id, int):
            return raw_id
        if isinstance(raw_id, str):
            if raw_id.isdigit():
                return int(raw_id)
            try:
                return int(GameAction.from_name(raw_id).value)
            except Exception:
                return fallback
        return fallback

    def _transition_reward(
        self,
        prev: FrameData,
        curr: FrameData,
        prev_features: FrameFeatures,
        curr_features: FrameFeatures,
    ) -> float:
        prev_levels = self._levels_completed(prev)
        curr_levels = self._levels_completed(curr)
        level_gain = max(0, curr_levels - prev_levels)
        state = getattr(curr, "state", GameState.NOT_FINISHED)
        novelty = 1.0 / (1.0 + self.visited[curr_features.fingerprint])
        delta = self._frame_delta_ratio(prev_features, curr_features)
        occupancy_shift = abs(curr_features.occupied - prev_features.occupied) / max(1, curr_features.width * curr_features.height)
        reward = 100.0 * level_gain + 2.0 * delta + 0.6 * novelty + 0.4 * occupancy_shift
        if state is GameState.WIN:
            reward += 1000.0
        elif state is GameState.GAME_OVER:
            reward -= 2.5
        elif state is GameState.NOT_FINISHED:
            reward += 0.02
        return reward

    def _levels_completed(self, frame: FrameData) -> int:
        value = getattr(frame, "levels_completed", None)
        if value is None:
            value = getattr(frame, "score", 0)
        try:
            return int(value)
        except Exception:
            return 0

    def _frame_delta_ratio(self, a: FrameFeatures, b: FrameFeatures) -> float:
        if a.width != b.width or a.height != b.height:
            return 1.0
        total = max(1, a.width * a.height)
        hist_distance = 0
        keys = set(a.histogram) | set(b.histogram)
        for key in keys:
            hist_distance += abs(a.histogram.get(key, 0) - b.histogram.get(key, 0))
        return min(1.0, hist_distance / (2.0 * total))

    def _to_grid(self, raw_frame: Any) -> Grid:
        if raw_frame is None:
            return []
        data = raw_frame
        if hasattr(data, "tolist"):
            data = data.tolist()
        if not isinstance(data, list) or not data:
            return []

        def is_number(x: Any) -> bool:
            return isinstance(x, (int, float, bool))

        try:
            if data and isinstance(data[0], list) and data[0] and is_number(data[0][0]):
                return [[self._cell_to_int(cell) for cell in row] for row in data if isinstance(row, list)]

            if (
                data
                and isinstance(data[0], list)
                and data[0]
                and isinstance(data[0][0], list)
                and data[0][0]
                and all(is_number(v) for v in data[0][0])
            ):
                height = len(data)
                width = len(data[0]) if height and isinstance(data[0], list) else 0
                if width and len(data[0][0]) <= 8:
                    return [
                        [self._vector_to_int(data[y][x]) for x in range(len(data[y]))]
                        for y in range(height)
                        if isinstance(data[y], list)
                    ]

            if (
                len(data) <= 8
                and isinstance(data[0], list)
                and data[0]
                and isinstance(data[0][0], list)
            ):
                channels = data
                height = len(channels[0])
                width = len(channels[0][0]) if height else 0
                grid: Grid = []
                for y in range(height):
                    row: list[int] = []
                    for x in range(width):
                        vector = []
                        for channel in channels:
                            try:
                                vector.append(channel[y][x])
                            except Exception:
                                vector.append(0)
                        row.append(self._vector_to_int(vector))
                    grid.append(row)
                return grid
        except Exception:
            return []
        return []

    def _cell_to_int(self, cell: Any) -> int:
        if isinstance(cell, bool):
            return int(cell)
        if isinstance(cell, (int, float)):
            return int(cell) & 0xFFFF
        if isinstance(cell, list):
            return self._vector_to_int(cell)
        return 0

    def _vector_to_int(self, values: Iterable[Any]) -> int:
        acc = 0
        for idx, value in enumerate(values):
            try:
                v = int(value) & 0xFF
            except Exception:
                v = 0
            acc = ((acc * 257) + v + idx + 1) & 0xFFFF
        return acc

    def _features(self, grid: Grid) -> FrameFeatures:
        height = len(grid)
        width = len(grid[0]) if height and grid[0] else 0
        if not height or not width:
            return FrameFeatures(
                fingerprint="empty",
                width=0,
                height=0,
                histogram={},
                background=0,
                occupied=0,
                bbox=None,
                components=[],
            )
        flat = [cell for row in grid for cell in row]
        hist_counter = Counter(flat)
        background = hist_counter.most_common(1)[0][0]
        occupied_cells: list[Coord] = []
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell != background:
                    occupied_cells.append((x, y))
        if occupied_cells:
            xs = [p[0] for p in occupied_cells]
            ys = [p[1] for p in occupied_cells]
            bbox = (min(xs), min(ys), max(xs), max(ys))
        else:
            bbox = None
        components = self._components(grid, background, max_components=16)
        fingerprint = self._fingerprint(grid, background, hist_counter, bbox, components)
        return FrameFeatures(
            fingerprint=fingerprint,
            width=width,
            height=height,
            histogram=dict(hist_counter),
            background=background,
            occupied=len(occupied_cells),
            bbox=bbox,
            components=components,
        )

    def _fingerprint(
        self,
        grid: Grid,
        background: int,
        hist: Counter[int],
        bbox: Optional[tuple[int, int, int, int]],
        components: list[dict[str, Any]],
    ) -> str:
        height = len(grid)
        width = len(grid[0]) if height else 0
        sample_parts: list[str] = [f"{width}x{height}", f"bg={background}"]
        sample_parts.append("h=" + ",".join(f"{k}:{hist[k]}" for k in sorted(hist)[:24]))
        sample_parts.append(f"bbox={bbox}")
        comp_sig = []
        for comp in components[:8]:
            comp_sig.append(
                f"{comp['color']}:{comp['size']}:{comp['cx']}:{comp['cy']}:{comp['bbox']}"
            )
        sample_parts.append("c=" + "|".join(comp_sig))
        stride_y = max(1, height // 16)
        stride_x = max(1, width // 16)
        sampled = []
        for y in range(0, height, stride_y):
            for x in range(0, width, stride_x):
                sampled.append(str(grid[y][x]))
        sample_parts.append("s=" + ",".join(sampled[:512]))
        return str(abs(hash(";".join(sample_parts))))

    def _components(self, grid: Grid, background: int, max_components: int) -> list[dict[str, Any]]:
        height = len(grid)
        width = len(grid[0]) if height else 0
        seen: set[Coord] = set()
        comps: list[dict[str, Any]] = []
        for y in range(height):
            for x in range(width):
                if (x, y) in seen or grid[y][x] == background:
                    continue
                color = grid[y][x]
                queue: deque[Coord] = deque([(x, y)])
                seen.add((x, y))
                cells: list[Coord] = []
                while queue:
                    cx, cy = queue.popleft()
                    cells.append((cx, cy))
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if nx < 0 or ny < 0 or nx >= width or ny >= height:
                            continue
                        if (nx, ny) in seen or grid[ny][nx] != color:
                            continue
                        seen.add((nx, ny))
                        queue.append((nx, ny))
                xs = [p[0] for p in cells]
                ys = [p[1] for p in cells]
                comps.append(
                    {
                        "color": color,
                        "size": len(cells),
                        "cx": int(round(sum(xs) / len(xs))),
                        "cy": int(round(sum(ys) / len(ys))),
                        "bbox": (min(xs), min(ys), max(xs), max(ys)),
                    }
                )
        comps.sort(key=lambda c: (-int(c["size"]), int(c["color"]), int(c["cy"]), int(c["cx"])))
        return comps[:max_components]

    def _changed_cells(self, a: Grid, b: Grid, limit: int) -> list[Coord]:
        height = min(len(a), len(b))
        width = min(len(a[0]) if a and a[0] else 0, len(b[0]) if b and b[0] else 0)
        out: list[Coord] = []
        for y in range(height):
            for x in range(width):
                if a[y][x] != b[y][x]:
                    out.append((x, y))
                    if len(out) >= limit:
                        return out
        return out

    def _log_transition(
        self,
        prev: FrameData,
        curr: FrameData,
        action_id: Optional[int],
        reward: float,
        changed: bool,
        features: FrameFeatures,
    ) -> None:
        if self.memory_path is None:
            return
        record = {
            "ts": round(time.time(), 6),
            "agent": self.VERSION,
            "game_id": self.game_id,
            "step": self.action_counter,
            "action_id": action_id,
            "reward": round(reward, 6),
            "changed": changed,
            "state": str(getattr(curr, "state", "")),
            "levels_completed": self._levels_completed(curr),
            "prev_levels_completed": self._levels_completed(prev),
            "fingerprint": features.fingerprint,
            "width": features.width,
            "height": features.height,
            "occupied": features.occupied,
            "bbox": features.bbox,
            "components": features.components[:8],
        }
        try:
            with self.memory_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
        except OSError:
            self.memory_path = None
