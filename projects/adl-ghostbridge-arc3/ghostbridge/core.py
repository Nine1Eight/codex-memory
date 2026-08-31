from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from world.causal import CausalTransitionGraph
from world.state import Action, Hypothesis, Reflection, WorldState, clamp01


@dataclass(slots=True)
class Gap:
    category: str
    required: str
    present: tuple[str, ...]
    missing: tuple[str, ...]
    evidence: tuple[str, ...]
    confidence: float


class GhostBridge:
    def __init__(self) -> None:
        self.hypotheses: dict[str, Hypothesis] = {}
        self.requested_detectors: set[str] = set()

    def find_gap(self, world: WorldState, graph: CausalTransitionGraph) -> Gap | None:
        present = tuple(sorted({e.kind for e in world.entities}))
        if world.player() is None:
            return Gap("missing_detector", "controllable entity", present, ("player detector",), (world.state_key,), 0.9)
        if not graph.reliable_actions(world, "progress", 0.45):
            return Gap("missing_relationship", "causal route to progress", present, ("action-to-progress edge",), (world.state_key,), 0.75)
        if world.uncertainty.get("goal", 1.0) > 0.6:
            return Gap("incorrect_goal_hypothesis", "observable goal condition", present, ("goal detector",), (world.state_key,), 0.65)
        return None

    def generate(self, gap: Gap, world: WorldState) -> list[Hypothesis]:
        available = world.available_actions
        tests = tuple((action,) for action in available)
        categories = {
            "missing_detector": "A moving component is the controllable entity",
            "missing_relationship": "One available action creates a prerequisite state for progress",
            "incorrect_goal_hypothesis": "A rare object or topology transition is the goal condition",
        }
        output = []
        for index, test in enumerate(tests or ((),)):
            claim = categories.get(gap.category, f"Resolve {gap.required}")
            hid = sha1(f"{world.state_key}|{gap.category}|{index}".encode()).hexdigest()[:12]
            hypothesis = Hypothesis(hid, claim, gap.category, list(gap.evidence), [], gap.confidence / max(1, len(tests)), {"gap_reduced": True}, test, len(test) * 0.05, 0.1, 0.8, 0.7)
            self.hypotheses[hid] = hypothesis; output.append(hypothesis)
        if gap.category == "missing_detector": self.requested_detectors.add("player")
        return output

    def best_hypothesis(self, gap: Gap, world: WorldState) -> Hypothesis:
        candidates = self.generate(gap, world)
        if not candidates: raise RuntimeError("gap produced no falsifiable hypothesis")
        return max(candidates, key=lambda h: h.utility())

    def update(self, reflection: Reflection) -> None:
        for hypothesis in self.hypotheses.values():
            if not hypothesis.active or not hypothesis.minimum_discriminating_test: continue
            if hypothesis.minimum_discriminating_test[0].key() != reflection.prediction.action.key(): continue
            if reflection.delta.changed:
                hypothesis.supporting_evidence.append(reflection.actual_state_key); hypothesis.confidence = clamp01(hypothesis.confidence + 0.15)
            else:
                hypothesis.contradictions.append(reflection.actual_state_key); hypothesis.confidence = clamp01(hypothesis.confidence - 0.3)
                if len(hypothesis.contradictions) >= 2 or hypothesis.confidence < 0.1: hypothesis.active = False
