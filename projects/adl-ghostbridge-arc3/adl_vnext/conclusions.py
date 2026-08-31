from __future__ import annotations

from typing import Any, Mapping

from .schemas import CanonicalRecord, EpistemicStatus, RecordType, Scope


FAILURE_CLASSES = {"perception", "experiment_selection", "hypothesis", "planning", "execution", "budget", "unresolved_mechanic"}


class ADLConclusionCompiler:
    def compile(self, scope: Scope, *, move: str, sequence: str, mechanic: str, strategy: str, game: str, partitions: Mapping[str, tuple[str, ...]], supporting: tuple[str, ...], contradictory: tuple[str, ...], alternatives: tuple[str, ...], assumptions: tuple[str, ...], falsification_tests: tuple[Mapping[str, Any], ...], strategic_implications: tuple[str, ...], ranked_experiments: tuple[str, ...], failure_class: str, provenance: tuple[str, ...]) -> CanonicalRecord:
        if failure_class not in FAILURE_CLASSES: raise ValueError(f"invalid failure class: {failure_class}")
        referenced = set(supporting) | set(contradictory) | set(provenance)
        if not referenced: raise ValueError("conclusion requires reconstructible ledger references")
        payload = {"move": move, "sequence": sequence, "mechanic": mechanic, "strategy": strategy, "game": game, "partitions": {key: tuple(value) for key,value in partitions.items()}, "supporting_evidence": supporting, "contradictory_evidence": contradictory, "alternative_explanations": alternatives, "assumptions": assumptions, "falsification_tests": falsification_tests, "strategic_implications": strategic_implications, "ranked_experiment_proposals": ranked_experiments, "failure_diagnosis": failure_class}
        return CanonicalRecord.create(RecordType.CONCLUSION_BUNDLE, scope, payload, provenance=provenance, status=EpistemicStatus.INFERRED, independence_group=f"conclusion:{scope.transition_id}")

