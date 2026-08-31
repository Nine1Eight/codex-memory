from __future__ import annotations

import math
import random
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Any

import numpy as np

from .utils import frame_array, frame_hash


@dataclass
class Proposal:
    action: int
    data: dict[str, Any] | None
    confidence: float
    source: str
    reason: str


class VoteLearnPolicy:
    def __init__(self, seed: int = 918):
        self.rng = random.Random(seed)
        self.value: dict[tuple[str, int], float] = defaultdict(float)
        self.trials: Counter[tuple[str, int]] = Counter()
        self.recent: deque[int] = deque(maxlen=12)
        self.last_hash: str | None = None
        self.palette_memory: dict[str, Counter[int]] = defaultdict(Counter)
        self.last_candidates: list[dict[str, Any]] = []
        self.last_choice: dict[str, Any] = {}

    def _click_candidates(self, frame: np.ndarray, game_tags: tuple[str, ...]) -> list[Proposal]:
        if "click" not in "_".join(game_tags) and "keyboard_click" not in "_".join(game_tags):
            return []
        props: list[Proposal] = []
        vals, counts = np.unique(frame, return_counts=True)
        # Prefer rare non-background pixels as clickable objects.
        candidates = []
        for v, c in zip(vals.tolist(), counts.tolist()):
            if v < 0:
                continue
            if c <= max(4, frame.size // 20):
                candidates.append((c, v))
        candidates.sort()
        for c, v in candidates[:4]:
            ys, xs = np.where(frame == v)
            if len(xs) == 0:
                continue
            x, y = int(round(xs.mean())), int(round(ys.mean()))
            props.append(Proposal(6, {"x": x, "y": y}, 0.20 + 0.02 * len(props), "blindsight_click", f"rare_color_{v}_count_{c}"))
        return props

    def proposals(self, frame: Any, game_id: str, available: list[int], game_tags: tuple[str, ...]) -> list[Proposal]:
        arr = frame_array(frame)
        state = frame_hash(arr)
        avail = set(int(a) for a in available if int(a) > 0) or {1, 2, 3, 4, 5, 6}
        props: list[Proposal] = []

        # Movement sweeps with learned state/action values and repeat penalty.
        for action in [1, 2, 3, 4, 5, 7]:
            if action not in avail:
                continue
            key = (state, action)
            conf = 0.12 + 0.08 * math.tanh(self.value[key]) - 0.04 * self.recent.count(action)
            if action == 5:
                conf += 0.03
            props.append(Proposal(action, None, max(0.01, min(0.95, conf)), "vote_learn", "state_action_value"))

        if 6 in avail:
            props.extend(self._click_candidates(arr, game_tags))

        # If everything is weak, deterministic scan. This avoids pure random loops.
        if not props:
            for action in sorted(avail):
                props.append(Proposal(action, None, 0.05, "fallback_scan", "available_action"))

        props.sort(key=lambda p: (p.confidence + 0.04 * math.tanh(self.value[(state, p.action)]), -self.recent.count(p.action)), reverse=True)
        return props

    def _proposal_record(self, state: str, p: Proposal) -> dict[str, Any]:
        key = (state, int(p.action))
        return {
            "action": int(p.action),
            "data": p.data,
            "confidence": round(float(p.confidence), 6),
            "source": p.source,
            "reason": p.reason,
            "repeat_count": int(self.recent.count(p.action)),
            "learned_value": round(float(self.value[key]), 6),
            "trials": int(self.trials[key]),
        }

    def choose(self, frame: Any, game_id: str, available: list[int], game_tags: tuple[str, ...]) -> Proposal:
        arr = frame_array(frame)
        state = frame_hash(arr)
        props = self.proposals(arr, game_id, available, game_tags)

        # Avoid repeating the same action too much unless it is the only option.
        filtered = [p for p in props if self.recent.count(p.action) < 4]
        p = (filtered or props)[0]

        self.last_candidates = [self._proposal_record(state, x) for x in props[:12]]
        self.last_choice = self._proposal_record(state, p)
        self.last_choice["filtered_candidates"] = len(filtered)
        self.last_choice["total_candidates"] = len(props)

        self.recent.append(p.action)
        return p

    def learn(self, before: Any, after: Any, action: int, reward: float, level_delta: int, done: bool) -> dict[str, Any]:
        state = frame_hash(before)
        key = (state, int(action))
        b = frame_array(before)
        a = frame_array(after)
        delta = int(np.sum(b != a)) if b.shape == a.shape else int(max(b.size, a.size))
        shaped = float(reward)
        outcome_tags = []
        if level_delta > 0:
            shaped += 2.0
            outcome_tags.append("level_advanced")
        if delta > 0:
            shaped += min(0.30, delta / max(64.0, float(b.size)))
            outcome_tags.append("frame_changed")
        else:
            shaped -= 0.35
            outcome_tags.append("no_frame_change")
        if done and level_delta <= 0:
            shaped -= 0.25
            outcome_tags.append("terminal_without_level_gain")

        self.trials[key] += 1
        # Conservative online update.
        old_value = float(self.value[key])
        self.value[key] = 0.85 * self.value[key] + shaped

        return {
            "state": state,
            "action": int(action),
            "delta": delta,
            "shaped_reward": round(float(shaped), 6),
            "old_value": round(old_value, 6),
            "new_value": round(float(self.value[key]), 6),
            "value": round(float(self.value[key]), 6),
            "trials": int(self.trials[key]),
            "outcome_tags": outcome_tags,
        }
