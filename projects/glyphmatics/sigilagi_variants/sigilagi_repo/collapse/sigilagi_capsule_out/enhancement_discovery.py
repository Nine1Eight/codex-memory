from __future__ import annotations
from typing import Dict, Any, List


class EnhancementDiscovery:
    """
    Very small deterministic heuristic recommender.
    """

    def discover(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs: List[Dict[str, Any]] = []

        docs = int(system_state.get("doc_count", 0))
        rules = int(system_state.get("discount_rule_count", 0))
        changes = int(system_state.get("change_count", 0))

        if docs < 3:
            recs.append({
                "priority": 10,
                "title": "Increase corpus breadth",
                "reason": "RAG quality is likely limited by sparse document coverage.",
            })
        if rules == 0:
            recs.append({
                "priority": 20,
                "title": "Add discount rules",
                "reason": "Combiner has no economic policy inputs.",
            })
        if changes > 5:
            recs.append({
                "priority": 30,
                "title": "Stabilize refinement patches",
                "reason": "High config churn indicates schema drift risk.",
            })
        if not recs:
            recs.append({
                "priority": 100,
                "title": "No immediate enhancement required",
                "reason": "Current state satisfies the minimal deterministic profile.",
            })

        recs.sort(key=lambda r: (r["priority"], r["title"]))
        return recs
