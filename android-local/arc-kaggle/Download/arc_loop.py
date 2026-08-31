from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import BridgePlan, CapabilityGraph, SystemSnapshot
from .runtime import CandidateAction, DifferenceFusionRuntime, FusionDecision, NegativeSpaceMap


class ARCEnvironmentLike(Protocol):
    """Small protocol for ARC-style environments used by the integration adapter."""

    def step(self, action: str) -> object:
        """Execute an action and return the environment result."""


@dataclass(frozen=True)
class ARCMoveTrace:
    """Move-level ADL trace consumed by GhostBridge before the next action."""

    move_index: int
    environment_signature: str
    proposed_actions: tuple[CandidateAction, ...]
    snapshot: SystemSnapshot


@dataclass(frozen=True)
class ARCMoveResult:
    """Result of one guarded ARC move."""

    move_index: int
    decision: FusionDecision
    executed_action: str | None
    environment_result: object | None
    negative_space_map: NegativeSpaceMap


class ARCPerMoveController:
    """Pre-action GhostBridge integration for ARC-style agent loops.

    The controller enforces the key invariant:

    An action that depends on a known missing capability is detected before
    env.step(action), not after the failure.
    """

    def __init__(self, graph: CapabilityGraph, instantiate_bridges: bool = False) -> None:
        self.runtime = DifferenceFusionRuntime(graph)
        self.instantiate_bridges = instantiate_bridges

    def preflight(self, trace: ARCMoveTrace) -> tuple[FusionDecision, NegativeSpaceMap]:
        negative_space_map = self.runtime.update_negative_space(trace.snapshot, move_index=trace.move_index)
        decision = self.runtime.choose(
            trace.proposed_actions,
            negative_space_map,
            instantiate_bridges=self.instantiate_bridges,
        )
        return decision, negative_space_map

    def guarded_step(self, env: ARCEnvironmentLike, trace: ARCMoveTrace) -> ARCMoveResult:
        decision, negative_space_map = self.preflight(trace)
        if decision.status in {"blocked", "no_action"} or decision.selected is None:
            return ARCMoveResult(
                move_index=trace.move_index,
                decision=decision,
                executed_action=None,
                environment_result=None,
                negative_space_map=negative_space_map,
            )
        if decision.status == "bridge_required" and not self.instantiate_bridges:
            return ARCMoveResult(
                move_index=trace.move_index,
                decision=decision,
                executed_action=None,
                environment_result=None,
                negative_space_map=negative_space_map,
            )
        result = env.step(decision.selected.name)
        return ARCMoveResult(
            move_index=trace.move_index,
            decision=decision,
            executed_action=decision.selected.name,
            environment_result=result,
            negative_space_map=negative_space_map,
        )

    @staticmethod
    def bridge_ids(decision: FusionDecision) -> tuple[str, ...]:
        return tuple(plan.gap.capability.id for plan in decision.required_bridges)

    @staticmethod
    def bridge_candidates(decision: FusionDecision) -> tuple[BridgePlan, ...]:
        return decision.required_bridges
