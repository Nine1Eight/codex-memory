from __future__ import annotations

from collections import Counter, deque

from world.causal import CausalTransitionGraph
from world.state import Action, Hypothesis, Plan, WorldState, clamp01
from world.twin import EnvironmentTwin


class ScoreAwarePlanner:
    def __init__(self, twin: EnvironmentTwin, graph: CausalTransitionGraph) -> None:
        self.twin = twin; self.graph = graph; self.action_trials: Counter[int] = Counter()

    def shortest_reliable_plan(self, world: WorldState) -> Plan | None:
        progress_states = {t.target_key for t in self.graph.transitions if t.delta.progress_delta > 0 or t.delta.outcome == "progress"}
        actions = self.graph.path(world.state_key, progress_states)
        if not actions:
            reliable = self.graph.reliable_actions(world, "progress", 0.55)
            actions = tuple(reliable[:1])
        if not actions: return None
        confidence = min(self.twin.prediction_accuracy, min((self.twin.predict(world, a).confidence for a in actions), default=0.0))
        return Plan(actions, "shortest learned route to progress", 0.8, 0.1, 0.0, confidence, "known_reliable")

    def minimum_discriminating_experiment(self, hypothesis: Hypothesis, world: WorldState) -> Plan:
        if not hypothesis.minimum_discriminating_test: raise RuntimeError("hypothesis has no executable discriminating test")
        actions = tuple(a for a in hypothesis.minimum_discriminating_test if a.action_id in {x.action_id for x in world.available_actions})
        if not actions: raise RuntimeError("hypothesis test is unavailable in current state")
        return Plan(actions, f"falsify {hypothesis.hypothesis_id}: {hypothesis.claim}", 0.2, hypothesis.estimated_failure_risk, hypothesis.information_gain, hypothesis.confidence, "ghostbridge")

    def best_progress_plan(self, world: WorldState) -> Plan:
        if not world.available_actions: raise RuntimeError("cannot plan without available actions")
        scored = []
        for action in world.available_actions:
            prediction = self.twin.predict(world, action)
            novelty = 1.0 / (1 + self.action_trials[action.action_id])
            utility = 2.5 * self.twin.estimate_progress_probability(world, action) + 0.7 * novelty - 1.8 * prediction.expected_failure - 0.02
            scored.append((utility, -action.action_id, action, novelty, prediction))
        _, _, action, novelty, prediction = max(scored)
        self.action_trials[action.action_id] += 1
        return Plan((action,), "highest score-aware expected utility", prediction.expected_progress, prediction.expected_failure, novelty, clamp01(max(0.1, prediction.confidence)), "progress")


class ActionValidationError(ValueError):
    """A proposed action violates the observed ARC action contract."""


class ActionValidator:
    def validate(self, action: Action, world: WorldState) -> Action:
        legal = {a.action_id: a for a in world.available_actions}
        if action.action_id not in legal: raise ActionValidationError(f"action {action.action_id} is unavailable; legal={sorted(legal)}")
        if action.action_id == 0: raise ActionValidationError("RESET cannot pass through the normal real-action boundary")
        data = dict(action.data)
        requires_coordinates = bool(data) or action.action_id == 6
        if requires_coordinates:
            if set(data) - {"x", "y", "game_id"}: raise ActionValidationError(f"unsupported action data keys: {sorted(set(data) - {'x','y','game_id'})}")
            if "x" not in data or "y" not in data: raise ActionValidationError("coordinate action requires x and y")
            x, y = data["x"], data["y"]
            if not isinstance(x, int) or not isinstance(y, int): raise ActionValidationError("coordinates must be integers")
            if not (0 <= x < world.width and 0 <= y < world.height): raise ActionValidationError(f"coordinate {(x, y)} outside {world.width}x{world.height}")
        return action
