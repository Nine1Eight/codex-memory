from __future__ import annotations

from collections import defaultdict, deque

from world.state import Action, CausalEdge, Reflection, Transition, WorldState, clamp01


class CausalTransitionGraph:
    def __init__(self) -> None:
        self.transitions: list[Transition] = []
        self.edges: dict[tuple[str, str, str], CausalEdge] = {}
        self.adjacency: dict[str, list[Transition]] = defaultdict(list)

    @staticmethod
    def context(state: WorldState) -> str:
        player = state.player()
        return f"level={state.level}|player={player.position if player else 'unknown'}|objects={len(state.entities)}"

    def update(self, before: WorldState, action: Action, after: WorldState, reflection: Reflection) -> None:
        context = self.context(before)
        transition = Transition(before.state_key, action, after.state_key, reflection.delta, {"context_key": context}, reflection.provenance)
        self.transitions.append(transition); self.adjacency[before.state_key].append(transition)
        effects = self._effects(reflection)
        cause = f"action:{action.key()}"
        for effect in effects:
            key = (cause, effect, context)
            edge = self.edges.setdefault(key, CausalEdge(cause, effect, context))
            if reflection.prediction_error <= 0.5: edge.support += 1
            else: edge.contradictions += 1
            # Bayesian-smoothed empirical confidence prevents one-shot causality.
            edge.confidence = clamp01((edge.support + 1) / (edge.support + edge.contradictions + 3))
            edge.provenance.append(f"{before.state_key}->{after.state_key}")

    @staticmethod
    def _effects(reflection: Reflection) -> tuple[str, ...]:
        effects = [f"outcome:{reflection.delta.outcome}"]
        effects.extend(f"entity:{c.kind.value}:{c.entity_id}" for c in reflection.delta.entity_changes)
        effects.extend(f"topology:{key}" for key in reflection.delta.topology_changes)
        if reflection.delta.progress_delta: effects.append("progress")
        return tuple(effects)

    def reliable_actions(self, state: WorldState, effect: str = "progress", threshold: float = 0.55) -> list[Action]:
        context = self.context(state); found = []
        for (cause, candidate_effect, candidate_context), edge in self.edges.items():
            if candidate_effect == effect and candidate_context == context and edge.confidence >= threshold:
                action_id = int(cause.split(":", 2)[1]); found.append(Action(action_id))
        return found

    def path(self, source: str, targets: set[str], max_depth: int = 32) -> tuple[Action, ...]:
        queue = deque([(source, ())]); seen = {source}
        while queue:
            state, actions = queue.popleft()
            if state in targets: return actions
            if len(actions) >= max_depth: continue
            for transition in self.adjacency.get(state, ()):
                if transition.target_key not in seen:
                    seen.add(transition.target_key); queue.append((transition.target_key, actions + (transition.action,)))
        return ()
