from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .schemas import PlannerPhase


@dataclass(frozen=True, slots=True)
class ExperimentDecision:
    mode: str
    action: Any
    utility: float
    rationale: str
    phase: PlannerPhase


class ExperimentPlanner:
    def __init__(self, zero_score_budget: int = 48) -> None:
        self.zero_score_budget = zero_score_budget

    def phase(self, state: dict[str, Any]) -> PlannerPhase:
        if state.get("prediction_failed"):
            return PlannerPhase.RECOVER
        if state.get("verified_macro"):
            return PlannerPhase.EXPLOIT_PROVEN_MACROS
        if state.get("reward_path_expanded"):
            return PlannerPhase.EXPAND_REWARD_PATH
        if state.get("reward_path_verified"):
            return PlannerPhase.VERIFY_REWARD_PATH
        if state.get("score_seen") and state.get("backtraced"):
            return PlannerPhase.VERIFY_REWARD_PATH
        if state.get("score_seen"):
            return PlannerPhase.BACKTRACE_REWARD
        if state.get("mechanics"):
            return PlannerPhase.FIRST_SCORE
        if state.get("objects"):
            return PlannerPhase.DISCOVER_MECHANICS
        if state.get("controls"):
            return PlannerPhase.DISCOVER_OBJECTS
        return PlannerPhase.MAP_CONTROLS

    def select(self, actions: Iterable[Any], predictions: dict[Any, dict[str, float]], state: dict[str, Any]) -> ExperimentDecision:
        actions = tuple(actions)
        if not actions:
            raise RuntimeError("no legal experiment actions")
        phase = self.phase(state)
        scored = []
        for action in actions:
            prediction = predictions.get(action, {})
            reward = float(prediction.get("reward", 0.0))
            information = float(prediction.get("information", 0.5))
            risk = float(prediction.get("risk", 0.0))
            if state.get("score_seen"):
                utility = 4.0 * reward + 0.8 * information - 2.0 * risk
            else:
                utility = 1.2 * reward + 2.0 * information - 1.5 * risk
            scored.append((utility, str(action), action))
        utility, _, action = max(scored)
        mode = "recover" if phase == PlannerPhase.RECOVER else "exploit" if state.get("score_seen") else "probe"
        return ExperimentDecision(mode, action, utility, f"{phase.value}: expected reward/information/risk", phase)

