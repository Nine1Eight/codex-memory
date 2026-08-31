from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from world.state import Action, Prediction, Reflection, WorldState, clamp01


@dataclass(slots=True)
class EffectStats:
    trials: int = 0
    movements: dict[str, tuple[tuple[int, int], tuple[int, int]]] = None  # type: ignore[assignment]
    progress_sum: float = 0.0
    failures: int = 0
    accuracy: float = 0.5

    def __post_init__(self) -> None:
        if self.movements is None: self.movements = {}


class EnvironmentTwin:
    def __init__(self) -> None:
        self.effects: dict[tuple[str, int], EffectStats] = defaultdict(EffectStats)
        self.global_effects: dict[int, EffectStats] = defaultdict(EffectStats)
        self.prediction_accuracy = 0.5

    @staticmethod
    def context(state: WorldState) -> str:
        return f"{state.identity.base_id}|L{state.level}|P{state.player().position if state.player() else '?'}"

    def predict(self, state: WorldState, action: Action) -> Prediction:
        local = self.effects[(self.context(state), action.action_id)]
        stats = local if local.trials else self.global_effects[action.action_id]
        confidence = clamp01(stats.accuracy * stats.trials / (stats.trials + 2))
        return Prediction(action, state.state_key, (f"action {action.action_id} available",), dict(stats.movements), {}, {}, stats.progress_sum / max(1, stats.trials), stats.failures / max(1, stats.trials), confidence, ("environment_twin",))

    def predict_sequence(self, state: WorldState, actions: tuple[Action, ...]) -> tuple[Prediction, ...]:
        return tuple(self.predict(state, action) for action in actions)

    def legal_actions(self, state: WorldState) -> tuple[Action, ...]:
        return state.available_actions

    def estimate_reachability(self, state: WorldState, target: tuple[int, int]) -> float:
        return 1.0 if target in state.free_space else 0.0

    def estimate_progress_probability(self, state: WorldState, action: Action) -> float:
        prediction = self.predict(state, action)
        return clamp01(prediction.confidence * max(0.0, prediction.expected_progress) + (0.05 if prediction.confidence == 0 else 0.0))

    def estimate_failure_probability(self, state: WorldState, action: Action) -> float:
        return self.predict(state, action).expected_failure

    def update(self, before: WorldState, reflection: Reflection) -> None:
        for stats in (self.effects[(self.context(before), reflection.prediction.action.action_id)], self.global_effects[reflection.prediction.action.action_id]):
            stats.trials += 1; stats.progress_sum += reflection.delta.progress_delta
            stats.failures += int(reflection.outcome.value == "FAILURE")
            stats.movements = {c.entity_id: (tuple(c.before["position"]), tuple(c.after["position"])) for c in reflection.delta.entity_changes if c.kind.value == "MOVED" and c.before and c.after}
            stats.accuracy = clamp01(0.8 * stats.accuracy + 0.2 * (1.0 - reflection.prediction_error))
        self.prediction_accuracy = clamp01(0.9 * self.prediction_accuracy + 0.1 * (1.0 - reflection.prediction_error))
