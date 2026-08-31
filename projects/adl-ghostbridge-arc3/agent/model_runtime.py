from __future__ import annotations

class ModelRuntime:
    """Optional abstraction boundary; deterministic core never depends on this class."""
    def reason(self, context): return {"available": False, "context_keys": sorted(context)}
    def infer_goal(self, world): return []
    def propose_hypotheses(self, gap): return []
    def reflect(self, reflection): return {"outcome": reflection.outcome.value}
