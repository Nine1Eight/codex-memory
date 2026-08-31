from __future__ import annotations

from collections import Counter


class Introspection:
    @staticmethod
    def snapshot(runtime) -> dict[str, object]:
        transitions = runtime.ledger.transitions
        return {"transitions": len(transitions), "games": len({x.game_id for x in transitions}), "phases": dict(Counter(x.planner_phase.value for x in transitions)), "ledger_digest": runtime.ledger.replay_digest(), "pending": tuple(sorted(runtime.temporal.pending)), "prediction_models": len(runtime.twin.effects), "hypotheses": len(runtime.hypotheses.hypotheses)}
