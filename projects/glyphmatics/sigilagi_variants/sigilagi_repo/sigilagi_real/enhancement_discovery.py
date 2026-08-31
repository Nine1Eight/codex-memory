from __future__ import annotations
from typing import Dict, Any, List


class EnhancementDiscovery:
    def discover(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        if state.get("change_count", 0) >= 3:
            findings.append({
                "priority": 100,
                "title": "No immediate enhancement required",
                "reason": "Current state satisfies the minimal deterministic profile.",
            })
        else:
            findings.append({
                "priority": 60,
                "title": "Increase deterministic coverage",
                "reason": "Observed change_count below target; expand orchestration validation.",
            })

        if state.get("doc_count", 0) < 2:
            findings.append({
                "priority": 50,
                "title": "Expand retrieval corpus",
                "reason": "Low document count reduces retrieval diversity.",
            })

        if state.get("discount_rule_count", 0) < 2:
            findings.append({
                "priority": 40,
                "title": "Increase pricing rule coverage",
                "reason": "Limited pricing rules reduce policy expressiveness.",
            })

        findings.sort(key=lambda x: (-x["priority"], x["title"]))
        return findings
