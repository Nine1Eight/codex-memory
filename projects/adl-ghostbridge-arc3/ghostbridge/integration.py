from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import threading
from typing import Any, Mapping

from .causal_graph import CalibratedCausalGraph
from .completeness import TransitionCompleteness
from .difference_engine import HierarchicalDifferenceEngine
from .environment_twin import EnvironmentTwinV5
from .event_extractor import EventExtractor
from .evidence_ledger import EvidenceLedger
from .experiment_planner import ExperimentPlanner
from .hypothesis_engine import HypothesisEngine
from .memory_tiers import QuarantinedMemory
from .object_tracker import PersistentObjectTracker
from .perception import BudgetedPerception
from .region_model import RegionModel
from .reward_path_model import RewardPathModel
from .schemas import (
    ActionEvidence, DeltaBundle, ImmutableObservation, PlannerPhase,
    PredictionAssessment, TransitionEnvelope, TypedEvent, canonical, evidence_id,
)
from .temporal_model import TemporalOwnership


def _grid(snapshot: Mapping[str, Any]) -> tuple[tuple[int, ...], ...]:
    value = snapshot.get("grid") or snapshot.get("frame") or ()
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        return tuple(tuple(int(cell) for cell in row) for row in value)
    return ()


def _action_parts(action: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(action, Mapping):
        name = str(action.get("id", action.get("action_id", action.get("name", action))))
        data = dict(action.get("data") or {})
        return name, data
    name = str(getattr(action, "id", getattr(action, "action_id", getattr(action, "name", action))))
    return name, dict(getattr(action, "data", {}) or {})


def _observation(game_id: str, step: int, snapshot: Mapping[str, Any]) -> ImmutableObservation:
    return ImmutableObservation.capture(
        game_id, step, _grid(snapshot), snapshot.get("score") or 0.0,
        snapshot.get("levels") or snapshot.get("level") or 0,
        snapshot.get("game_over") or snapshot.get("terminal") or False,
        {"signature": snapshot.get("signature"), "won": snapshot.get("won")},
    )


class GhostBridgeV5Runtime:
    """Production transition boundary: capture, stabilize, explain, predict, commit."""

    def __init__(self, ledger_path: str | Path | None = None) -> None:
        self.ledger = EvidenceLedger(ledger_path)
        self.perception = BudgetedPerception(); self.objects = PersistentObjectTracker(); self.regions = RegionModel()
        self.difference = HierarchicalDifferenceEngine(); self.events = EventExtractor(); self.causal = CalibratedCausalGraph()
        self.hypotheses = HypothesisEngine(); self.twin = EnvironmentTwinV5(); self.reward = RewardPathModel()
        self.planner = ExperimentPlanner(); self.memory = QuarantinedMemory(); self.temporal = TemporalOwnership()
        self.completeness = TransitionCompleteness(); self.game_state: dict[str, dict[str, Any]] = {}
        self.steps: dict[str, int] = {}; self._pending_action: dict[str, ActionEvidence] = {}; self._lock = threading.RLock()

    def prepare(self, game_id: str, action: Any, before: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            step = self.steps.get(game_id, 0) + 1
            pre = _observation(game_id, step - 1, before)
            name, data = _action_parts(action)
            action_record = ActionEvidence.capture(game_id, step, name, data, pre.observation_id)
            self.temporal.begin(game_id, step, pre, action_record)
            self._pending_action[game_id] = action_record
            context = self._context(pre)
            return {"game_id": game_id, "step": step, "pre_observation_id": pre.observation_id, "action_id": action_record.action_id, "prediction": self.twin.predict(context, name), "phase": self.planner.phase(self.game_state.get(game_id, {})).value}

    def commit(self, game_id: str, after: Mapping[str, Any], intermediate: tuple[Mapping[str, Any], ...] = ()) -> TransitionEnvelope:
        with self._lock:
            pending = self.temporal.pending.get(game_id)
            action = self._pending_action.get(game_id)
            if pending is None or action is None:
                raise RuntimeError(f"no prepared transition for {game_id}")
            snapshots = tuple(intermediate) + (after,)
            for index, snapshot in enumerate(snapshots):
                observation = _observation(game_id, pending.step, snapshot)
                self.temporal.observe(game_id, observation, authoritative=index == len(snapshots) - 1)
            post, stabilization_ids = self.temporal.settle(game_id)
            pre = pending.pre; context = self._context(pre)
            cheap_pre = self.perception.cheap(pre); cheap_post = self.perception.cheap(post)
            force_expensive = self.perception.needs_expensive(cheap_pre, cheap_post, post.score - pre.score)
            delta = self.difference.diff(pre, post, force_expensive)
            events = self.events.extract(action, delta)
            prediction = self.twin.predict(context, action.action)
            assessment = self.twin.assess(prediction, events)
            state = self.game_state.setdefault(game_id, {})
            phase = self.planner.phase(state)
            hashes = {
                "pre": pre.observation_id, "action": action.action_id, "post": post.observation_id,
                "delta": delta.delta_id,
                "events": sha256(canonical([event.event_id for event in events]).encode()).hexdigest(),
            }
            material = {"game": game_id, "step": pending.step, **hashes}
            transition_id = evidence_id("transition", material, tuple(hashes.values()))
            hypothesis_updates = self.hypotheses.update(events, context)
            envelope = TransitionEnvelope(transition_id, game_id, pending.step, pre, action, post, stabilization_ids, delta, events, prediction, assessment, hypothesis_updates, (), phase, hashes)
            report = self.completeness.check(envelope)
            if not report.complete:
                raise RuntimeError(f"transition cannot train model: {report.missing}")
            reward_attribution = self.reward.attribute(envelope)
            envelope = replace(envelope, reward_attribution=reward_attribution)
            envelope.verify()
            self.ledger.commit(envelope)
            # Model updates occur only after the immutable envelope passes all checks.
            self.causal.update(action, events, context); self.twin.update(context, action.action, events, assessment)
            self.objects.update(post)
            if force_expensive: self.regions.topology(post)
            state.update({"controls": True, "objects": force_expensive or state.get("objects"), "mechanics": bool(self.causal.beliefs), "score_seen": state.get("score_seen", False) or delta.score_delta > 0 or delta.level_delta > 0, "backtraced": bool(reward_attribution), "prediction_failed": assessment.error > 0.7})
            self.memory.observe(game_id, context, f"action:{action.action}", tuple(event.event_type for event in events), delta.score_delta > 0 or delta.level_delta > 0)
            self.steps[game_id] = pending.step; del self._pending_action[game_id]
            return envelope

    @staticmethod
    def _context(observation: ImmutableObservation) -> str:
        return f"{observation.game_id}|L{observation.level}|{observation.frame_hash[:12]}"

    def assert_zero_debt(self, game_id: str) -> None:
        if game_id in self.temporal.pending or game_id in self._pending_action:
            raise RuntimeError(f"GhostBridge v5 transition debt remains for {game_id}")


def envelope_from_dict(value: Mapping[str, Any]) -> TransitionEnvelope:
    def observation(raw): return ImmutableObservation(**raw)
    def action(raw): return ActionEvidence(**raw)
    def delta(raw):
        raw = dict(raw); raw["changed_cells"] = tuple(tuple(x) for x in raw["changed_cells"]); raw["object_events"] = tuple(raw["object_events"]); raw["topology_events"] = tuple(raw["topology_events"])
        return DeltaBundle(**raw)
    def event(raw): return TypedEvent(**raw)
    assessment = PredictionAssessment(**value["assessment"])
    return TransitionEnvelope(value["transition_id"], value["game_id"], value["step"], observation(value["pre_observation"]), action(value["action"]), observation(value["post_observation"]), tuple(value["stabilization_observations"]), delta(value["delta"]), tuple(event(x) for x in value["events"]), value["prediction"], assessment, tuple(value["hypothesis_updates"]), tuple(value["reward_attribution"]), PlannerPhase(value["planner_phase"]), value["hashes"])

