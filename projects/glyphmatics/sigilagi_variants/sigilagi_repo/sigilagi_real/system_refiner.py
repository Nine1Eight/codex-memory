from __future__ import annotations
from copy import deepcopy
from typing import Dict, Any, List


class SystemRefiner:
    def refine(self, base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        config = deepcopy(base)
        changes: List[Dict[str, Any]] = []

        def merge(dst: Dict[str, Any], src: Dict[str, Any], prefix: str = "") -> None:
            for key, value in src.items():
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict) and isinstance(dst.get(key), dict):
                    merge(dst[key], value, path)
                else:
                    if key in dst:
                        changes.append({"op": "replace", "path": path, "before": dst[key], "after": value})
                    else:
                        changes.append({"op": "add", "path": path, "value": value})
                    dst[key] = value

        merge(config, delta)
        return {"config": config, "changes": changes, "change_count": len(changes)}
