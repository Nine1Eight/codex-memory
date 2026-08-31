from __future__ import annotations
from typing import Dict, Any, List


class SystemRefiner:
    """
    Deterministic config refinement:
    - deep-merge dictionaries
    - track change log
    """

    def refine(self, base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged, changes = self._merge(base, patch, path=[])
        return {
            "config": merged,
            "changes": changes,
            "change_count": len(changes),
        }

    def _merge(self, base: Any, patch: Any, path: List[str]) -> tuple[Any, List[Dict[str, Any]]]:
        changes: List[Dict[str, Any]] = []

        if isinstance(base, dict) and isinstance(patch, dict):
            out = dict(base)
            for key, patch_val in patch.items():
                next_path = path + [str(key)]
                if key in out:
                    out[key], sub = self._merge(out[key], patch_val, next_path)
                    changes.extend(sub)
                else:
                    out[key] = patch_val
                    changes.append({"op": "add", "path": ".".join(next_path), "value": patch_val})
            return out, changes

        if base != patch:
            changes.append({"op": "replace", "path": ".".join(path), "before": base, "after": patch})
        return patch, changes
