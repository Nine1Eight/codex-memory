from __future__ import annotations

from dataclasses import dataclass

from ghostbridge.core import Gap
from world.causal import CausalTransitionGraph
from world.state import Action, WorldState


@dataclass(slots=True)
class ReversePathResult:
    forward_frontier: frozenset[str]
    reverse_frontier: frozenset[str]
    connecting_actions: tuple[Action, ...]
    gap: Gap | None


class ReversePath:
    def analyze(self, world: WorldState, graph: CausalTransitionGraph) -> ReversePathResult:
        forward = {world.state_key}
        frontier = {world.state_key}
        for _ in range(8):
            nxt = {t.target_key for key in frontier for t in graph.adjacency.get(key, ())}
            nxt -= forward
            if not nxt: break
            forward |= nxt; frontier = nxt
        success_states = {t.target_key for t in graph.transitions if t.delta.progress_delta > 0 or t.delta.outcome == "progress"}
        reverse = set(success_states)
        frontier = set(success_states)
        for _ in range(8):
            nxt = {t.source_key for t in graph.transitions if t.target_key in frontier} - reverse
            if not nxt: break
            reverse |= nxt; frontier = nxt
        overlap = forward & reverse
        actions = graph.path(world.state_key, success_states) if overlap else ()
        gap = None if overlap else Gap("missing_route", "forward/reverse frontier connection", tuple(sorted(forward)), ("unobserved prerequisite or action",), tuple(sorted(reverse)), 0.7)
        return ReversePathResult(frozenset(forward), frozenset(reverse), actions, gap)
