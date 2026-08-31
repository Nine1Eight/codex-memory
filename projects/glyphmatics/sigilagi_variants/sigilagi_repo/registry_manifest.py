from __future__ import annotations
from typing import Dict, Any, List


class RegistryManifest:
    def __init__(self) -> None:
        self._manifest: Dict[str, Any] = {
            "system": "SigilAGI",
            "version": "v5",
            "slice": "core-control-retrieval-pricing-discovery-registry",
            "layers": {
                "retrieval": True,
                "control": True,
                "pricing": True,
                "discovery": True,
                "registry": True,
            },
            "modules": [],
            "state": {
                "boot_verified": False,
                "rehydrated": False,
            },
        }

    def register_modules(self, modules: List[str]) -> None:
        self._manifest["modules"] = sorted(modules)

    def apply_state(self, **kwargs: Any) -> None:
        self._manifest["state"].update(kwargs)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "system": self._manifest["system"],
            "version": self._manifest["version"],
            "slice": self._manifest["slice"],
            "layers": dict(self._manifest["layers"]),
            "modules": list(self._manifest["modules"]),
            "state": dict(self._manifest["state"]),
        }
