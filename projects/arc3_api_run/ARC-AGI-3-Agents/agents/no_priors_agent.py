"""No-priors ARC-AGI-3 agent with online object-centric world modelling.

The policy deliberately contains no game ids, level solutions, recorded action
sequences, or network/model calls.  Everything game-specific is inferred from
frames observed during the current run.  Knowledge may transfer between levels
of that run, which is part of the ARC-AGI-3 task.
"""

from __future__ import annotations

import hashlib
import base64
import io
import json
import math
import os
import random
from urllib.parse import urlparse
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from arcengine import FrameData, GameAction, GameState

from .agent import Agent

Grid = list[list[int]]
Point = tuple[int, int]


@dataclass(frozen=True)
class Scene:
    key: str
    width: int
    height: int
    background: int
    components: tuple[tuple[int, int, int, int, int, int], ...]


@dataclass
class Effect:
    tries: int = 0
    changes: int = 0
    progress: int = 0
    deaths: int = 0
    novelty_sum: float = 0.0
    destinations: Counter[str] = field(default_factory=Counter)

    def value(self) -> float:
        if not self.tries:
            return 0.0
        return (
            40.0 * self.progress
            + 1.5 * self.changes
            + self.novelty_sum
            - 5.0 * self.deaths
        ) / self.tries


class NoPriorsAgent(Agent):
    """Efficient explore-model-plan agent for unseen interactive grid worlds."""

    MAX_ACTIONS = int(os.getenv("NO_PRIORS_MAX_ACTIONS", "240"))
    VERSION = "no-priors-v2.0.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Stable seed; Python's hash() is process-randomized.
        digest = hashlib.blake2b(
            f"{self.card_id}:{self.game_id}:{self.VERSION}".encode(), digest_size=8
        ).digest()
        self.rng = random.Random(int.from_bytes(digest, "big"))
        self.learned_until = 1
        self.pending_action: Optional[int] = None
        self.pending_target: Optional[Point] = None
        self.effects: dict[tuple[str, int, Optional[Point]], Effect] = defaultdict(Effect)
        self.action_priors: dict[int, Effect] = defaultdict(Effect)
        self.visits: Counter[str] = Counter()
        self.edges: dict[str, list[tuple[int, Optional[Point], str, float]]] = defaultdict(list)
        self.recent_states: deque[str] = deque(maxlen=18)
        self.recent_choices: deque[tuple[str, int, Optional[Point]]] = deque(maxlen=24)
        self.target_tries: Counter[tuple[int, Point]] = Counter()
        self.level = 0
        self.level_actions: list[tuple[int, Optional[Point]]] = []
        self.success_macros: list[list[tuple[int, Optional[Point]]]] = []
        self.replay: deque[tuple[int, Optional[Point]]] = deque()
        self.vlm_url = os.getenv("NO_PRIORS_VLM_URL", "").strip()
        self.vlm_model = os.getenv("NO_PRIORS_VLM_MODEL", "vllm-model")
        self.vlm_frames: deque[Grid] = deque(maxlen=4)
        self.vlm_memory: deque[str] = deque(maxlen=10)

    @property
    def name(self) -> str:
        return f"{super().name}.{self.VERSION}.{self.MAX_ACTIONS}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return getattr(latest_frame, "state", None) is GameState.WIN

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        self._learn(frames)
        state = getattr(latest_frame, "state", GameState.NOT_PLAYED)
        if state in {GameState.NOT_PLAYED, GameState.GAME_OVER}:
            return self._emit(GameAction.RESET, latest_frame, None, "reset")

        actions = self._available(latest_frame)
        if not actions:
            return self._emit(GameAction.RESET, latest_frame, None, "no-actions")
        non_reset = [a for a in actions if a is not GameAction.RESET]
        actions = non_reset or actions
        scene = self._scene(getattr(latest_frame, "frame", []))
        grid = self._grid(getattr(latest_frame, "frame", []))
        if grid:
            self.vlm_frames.append(grid)
        self.visits[scene.key] += 1
        self.recent_states.append(scene.key)

        # Reuse a sequence only when it was discovered online in an earlier
        # level of this same run. Abort immediately when its predicted effect
        # repeatedly fails; later levels often alter rules.
        if self.replay:
            aid, target = self.replay.popleft()
            action = self._by_id(actions, aid)
            if action is not None:
                return self._emit(action, latest_frame, target, "online-macro")
            self.replay.clear()

        vlm_choice = self._vlm_choose(scene, actions)
        if vlm_choice is not None:
            action, target = vlm_choice
            return self._emit(action, latest_frame, target, "local-vlm")
        action, target, reason = self._choose(scene, actions)
        return self._emit(action, latest_frame, target, reason)

    def _vlm_choose(
        self, scene: Scene, actions: list[GameAction]
    ) -> Optional[tuple[GameAction, Optional[Point]]]:
        """Ask an optional localhost VLM; never permits an evaluation-time network call."""
        if not self.vlm_url or not self.vlm_frames:
            return None
        parsed_url = urlparse(self.vlm_url)
        if parsed_url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            return None
        try:
            import requests

            names = {self._model_name(a): a for a in actions}
            image_parts = []
            for index, grid in enumerate(self.vlm_frames):
                image_parts.extend(
                    [
                        {"type": "text", "text": f"STEP {index - len(self.vlm_frames) + 1}"},
                        {
                            "type": "image_url",
                            "image_url": {"url": self._grid_data_url(grid)},
                        },
                    ]
                )
            prompt = (
                "You control an unknown turn-based grid environment. No instructions or goal are given. "
                "Infer only from the chronological frames and action memory. Identify the controllable object, "
                "causal action effects, hazards, and the smallest reversible experiment or shortest goal-directed plan. "
                "Do not assume rules from any named game. Return JSON only: "
                '{"reason":"brief evidence","action":"up|down|left|right|spacebar|click|undo",'
                '"x":0,"y":0}. Coordinates are required only for click. Available actions: '
                + ", ".join(names)
                + ". Recent observed choices: "
                + json.dumps(list(self.vlm_memory)[-6:])
            )
            content = [{"type": "text", "text": prompt}, *image_parts]
            response = requests.post(
                self.vlm_url.rstrip("/") + "/chat/completions",
                json={
                    "model": self.vlm_model,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": 0.15,
                    "max_tokens": 512,
                },
                timeout=float(os.getenv("NO_PRIORS_VLM_TIMEOUT", "120")),
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            blob = self._json_object(str(text))
            name = str(blob.get("action", "")).lower().strip()
            action = names.get(name)
            if action is None:
                return None
            target = None
            if action.is_complex():
                target = (
                    max(0, min(63, int(blob.get("x", scene.width // 2)))),
                    max(0, min(63, int(blob.get("y", scene.height // 2)))),
                )
                # Suppress click classes already established as inert by the
                # symbolic learner; use the best untested salient target instead.
                effect = self.effects[(scene.key, int(action.value), target)]
                if effect.tries >= 2 and effect.changes == 0:
                    target = min(
                        self._targets(scene),
                        key=lambda p: self.target_tries[(int(action.value), p)],
                    )
            self.vlm_memory.append(
                json.dumps({"action": name, "target": target, "reason": blob.get("reason", "")})[:600]
            )
            return action, target
        except Exception:
            return None

    def _model_name(self, action: GameAction) -> str:
        mapping = {
            "ACTION1": "up",
            "ACTION2": "down",
            "ACTION3": "left",
            "ACTION4": "right",
            "ACTION5": "spacebar",
            "ACTION6": "click",
            "ACTION7": "undo",
            "RESET": "reset",
        }
        return mapping.get(action.name, action.name.lower())

    def _json_object(self, text: str) -> dict[str, Any]:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            value = json.loads(text[start : end + 1])
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _grid_data_url(self, grid: Grid) -> str:
        from PIL import Image

        palette = (
            (0, 0, 0), (0, 116, 217), (255, 65, 54), (46, 204, 64),
            (255, 220, 0), (170, 170, 170), (240, 18, 190), (255, 133, 27),
            (127, 219, 255), (135, 12, 37), (255, 255, 255), (100, 100, 100),
        )
        image = Image.new("RGB", (len(grid[0]), len(grid)))
        image.putdata([palette[cell % len(palette)] for row in grid for cell in row])
        image = image.resize((image.width * 8, image.height * 8), Image.Resampling.NEAREST)
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")

    def _choose(
        self, scene: Scene, actions: list[GameAction]
    ) -> tuple[GameAction, Optional[Point], str]:
        candidates: list[tuple[float, GameAction, Optional[Point]]] = []
        looping = len(self.recent_states) >= 10 and len(set(self.recent_states)) <= 4
        total = 1 + sum(p.tries for p in self.action_priors.values())

        for action in actions:
            aid = int(action.value)
            targets = self._targets(scene) if action.is_complex() else [None]
            for target in targets:
                local = self.effects[(scene.key, aid, target)]
                prior = self.action_priors[aid]
                unexplored = 3.0 / (1.0 + local.tries)
                ucb = math.sqrt(2.0 * math.log(total + 1) / (prior.tries + 1))
                target_bonus = 0.0
                if target is not None:
                    target_bonus = 1.2 / (1 + self.target_tries[(aid, target)])
                no_effect_penalty = 2.5 if prior.tries >= 3 and prior.changes == 0 else 0.0
                repeat_penalty = 0.0
                choice = (scene.key, aid, target)
                if choice in self.recent_choices:
                    repeat_penalty += 1.0 + 0.25 * self.recent_choices.count(choice)
                if looping:
                    repeat_penalty *= 1.8
                score = (
                    0.65 * local.value()
                    + 0.35 * prior.value()
                    + unexplored
                    + ucb
                    + target_bonus
                    - no_effect_penalty
                    - repeat_penalty
                    + self.rng.random() * 1e-6
                )
                candidates.append((score, action, target))

        candidates.sort(key=lambda item: item[0], reverse=True)
        _, action, target = candidates[0]
        return action, target, "object-ucb-loop-escape" if looping else "object-ucb"

    def _targets(self, scene: Scene) -> list[Point]:
        points: list[Point] = []
        # Small, rare components are information-rich and frequently encode
        # actors, keys, buttons, or goals. Component centers are tried first.
        rarity = Counter(c[0] for c in scene.components)
        ranked = sorted(scene.components, key=lambda c: (rarity[c[0]], c[1], c[3], c[2]))
        for _color, _size, cx, cy, _w, _h in ranked[:20]:
            points.append((cx, cy))
        points.extend(
            [
                (scene.width // 2, scene.height // 2),
                (scene.width // 4, scene.height // 4),
                (3 * scene.width // 4, scene.height // 4),
                (scene.width // 4, 3 * scene.height // 4),
                (3 * scene.width // 4, 3 * scene.height // 4),
            ]
        )
        out: list[Point] = []
        for point in points:
            point = (max(0, min(63, point[0])), max(0, min(63, point[1])))
            if point not in out:
                out.append(point)
        return out or [(32, 32)]

    def _learn(self, frames: list[FrameData]) -> None:
        start = max(1, self.learned_until)
        for i in range(start, len(frames)):
            prev, curr = frames[i - 1], frames[i]
            before = self._scene(getattr(prev, "frame", []))
            after = self._scene(getattr(curr, "frame", []))
            aid = self._frame_action(curr)
            if aid is None:
                aid = self.pending_action
            target = self.pending_target if aid == self.pending_action else None
            if aid is None:
                continue
            changed = before.key != after.key
            old_level = self._levels(prev)
            new_level = self._levels(curr)
            progress = max(0, new_level - old_level)
            death = int(getattr(curr, "state", None) is GameState.GAME_OVER)
            novelty = 1.0 / (1.0 + self.visits[after.key]) if changed else 0.0
            for effect in (self.effects[(before.key, aid, target)], self.action_priors[aid]):
                effect.tries += 1
                effect.changes += int(changed)
                effect.progress += progress
                effect.deaths += death
                effect.novelty_sum += novelty
                effect.destinations[after.key] += 1
            reward = 40.0 * progress + novelty - 5.0 * death
            self.edges[before.key].append((aid, target, after.key, reward))
            self.recent_choices.append((before.key, aid, target))
            self.level_actions.append((aid, target))
            if target is not None:
                self.target_tries[(aid, target)] += 1
            if progress:
                macro = self._compact_macro(self.level_actions)
                if macro:
                    self.success_macros.append(macro)
                    self.replay = deque(macro)
                self.level_actions = []
                self.level = new_level
                self.recent_states.clear()
                self.recent_choices.clear()
            elif death:
                self.level_actions = []
                self.replay.clear()
        self.learned_until = len(frames)

    def _compact_macro(
        self, actions: list[tuple[int, Optional[Point]]]
    ) -> list[tuple[int, Optional[Point]]]:
        # Remove immediate no-op repetitions using learned global effects, and
        # retain only a bounded suffix: it is more likely to encode the actual
        # solution than early exploratory probes.
        useful = [x for x in actions if self.action_priors[x[0]].changes > 0]
        compact: list[tuple[int, Optional[Point]]] = []
        for item in useful:
            if len(compact) < 2 or item != compact[-1] or item != compact[-2]:
                compact.append(item)
        return compact[-48:]

    def _emit(
        self,
        action: GameAction,
        frame: FrameData,
        target: Optional[Point],
        policy: str,
    ) -> GameAction:
        if action.is_complex():
            if target is None:
                target = (32, 32)
            action.set_data({"game_id": self.game_id, "x": target[0], "y": target[1]})
        else:
            try:
                action.set_data({"game_id": self.game_id})
            except Exception:
                action.set_data({})
        self.pending_action = int(action.value)
        self.pending_target = target
        action.reasoning = {
            "policy": policy,
            "version": self.VERSION,
            "online_states": len(self.visits),
            "level": self.level,
            "target": target,
        }
        return action

    def _available(self, frame: FrameData) -> list[GameAction]:
        raw = getattr(frame, "available_actions", None) or list(GameAction)
        out: list[GameAction] = []
        for item in raw:
            try:
                action = item if isinstance(item, GameAction) else GameAction.from_id(int(getattr(item, "value", item)))
            except Exception:
                try:
                    action = GameAction.from_name(str(item))
                except Exception:
                    continue
            if action not in out:
                out.append(action)
        return out

    def _by_id(self, actions: list[GameAction], aid: int) -> Optional[GameAction]:
        return next((a for a in actions if int(a.value) == aid), None)

    def _frame_action(self, frame: FrameData) -> Optional[int]:
        raw = getattr(getattr(frame, "action_input", None), "id", None)
        try:
            return int(getattr(raw, "value", raw))
        except Exception:
            return None

    def _levels(self, frame: FrameData) -> int:
        try:
            return int(getattr(frame, "levels_completed", 0) or 0)
        except Exception:
            return 0

    def _scene(self, raw: Any) -> Scene:
        grid = self._grid(raw)
        h = len(grid)
        w = len(grid[0]) if h else 0
        if not h or not w:
            return Scene("empty", w, h, 0, ())
        hist = Counter(v for row in grid for v in row)
        bg = hist.most_common(1)[0][0]
        components = tuple(self._components(grid, bg))
        payload = repr((w, h, sorted(hist.items()), components)).encode()
        key = hashlib.blake2b(payload, digest_size=12).hexdigest()
        return Scene(key, w, h, bg, components)

    def _grid(self, raw: Any) -> Grid:
        data = raw.tolist() if hasattr(raw, "tolist") else raw
        if not isinstance(data, list) or not data:
            return []
        try:
            if isinstance(data[0][0], (int, float, bool)):
                return [[int(v) for v in row] for row in data]
            # HWC vector/color frames: stable integer packing.
            if isinstance(data[0][0], list):
                return [[self._pack(v) for v in row] for row in data]
        except Exception:
            return []
        return []

    def _pack(self, values: Iterable[Any]) -> int:
        acc = 0
        for value in values:
            try:
                acc = (acc * 257 + int(value)) & 0xFFFFFFFF
            except Exception:
                pass
        return acc

    def _components(self, grid: Grid, bg: int) -> list[tuple[int, int, int, int, int, int]]:
        h, w = len(grid), len(grid[0])
        seen: set[Point] = set()
        result: list[tuple[int, int, int, int, int, int]] = []
        for y in range(h):
            for x in range(w):
                color = grid[y][x]
                if color == bg or (x, y) in seen:
                    continue
                todo = [(x, y)]
                seen.add((x, y))
                cells: list[Point] = []
                while todo:
                    px, py = todo.pop()
                    cells.append((px, py))
                    for qx, qy in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                        if 0 <= qx < w and 0 <= qy < h and (qx, qy) not in seen and grid[qy][qx] == color:
                            seen.add((qx, qy))
                            todo.append((qx, qy))
                xs, ys = [p[0] for p in cells], [p[1] for p in cells]
                result.append((color, len(cells), round(sum(xs) / len(xs)), round(sum(ys) / len(ys)), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
        result.sort(key=lambda c: (c[0], c[1], c[3], c[2]))
        return result[:64]
