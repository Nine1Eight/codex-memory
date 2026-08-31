from __future__ import annotations

from world.state import OutcomeClass, Prediction, Reflection, WorldDelta, WorldState, clamp01


class ReflectionEngine:
    def reflect(self, prediction: Prediction, actual: WorldState, delta: WorldDelta) -> Reflection:
        predicted_change = bool(prediction.expected_movement or prediction.expected_object_changes or prediction.expected_topology_changes or prediction.expected_progress)
        actual_change = delta.changed
        errors = []
        if predicted_change != actual_change: errors.append("change_presence")
        progress_error = abs(prediction.expected_progress - delta.progress_delta)
        error = clamp01((len(errors) + progress_error + (1.0 if actual.failed and prediction.expected_failure < 0.5 else 0.0)) / 3.0)
        if actual.failed: outcome = OutcomeClass.FAILURE
        elif delta.progress_delta > 0 or actual.level_complete: outcome = OutcomeClass.PROGRESS
        elif error <= 0.15: outcome = OutcomeClass.CONFIRMED
        elif error <= 0.5: outcome = OutcomeClass.PARTIAL
        elif actual_change and not predicted_change: outcome = OutcomeClass.NOVEL
        else: outcome = OutcomeClass.CONTRADICTION
        confirmed = ("change_presence",) if predicted_change == actual_change else ()
        novel = tuple(sorted(delta.topology_changes)) if outcome is OutcomeClass.NOVEL else ()
        score = delta.progress_delta + (1.0 if actual.level_complete else 0.0) - (1.0 if actual.failed else 0.0) - 0.1 * error
        return Reflection(outcome, prediction, actual.state_key, delta, error, confirmed, tuple(errors), novel, score, (prediction.state_key, actual.state_key))
