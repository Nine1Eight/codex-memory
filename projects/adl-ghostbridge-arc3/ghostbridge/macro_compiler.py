from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable

from .schemas import canonical


@dataclass(frozen=True, slots=True)
class GuardedMacro:
    macro_id: str
    actions: tuple[Any, ...]
    preconditions: tuple[Callable[[Any], bool], ...]
    postconditions: tuple[Callable[[Any], bool], ...]
    evidence_paths: tuple[str, ...]
    independent_successes: int


class MacroCompiler:
    def compile(self, actions, preconditions, postconditions, evidence_paths, independent_successes: int) -> GuardedMacro:
        if independent_successes < 2:
            raise ValueError("reward path must succeed independently twice before macro compilation")
        actions = tuple(actions); evidence_paths = tuple(evidence_paths)
        material = {"actions": [str(x) for x in actions], "evidence": evidence_paths, "successes": independent_successes}
        return GuardedMacro("mac-" + sha256(canonical(material).encode()).hexdigest()[:20], actions, tuple(preconditions), tuple(postconditions), evidence_paths, independent_successes)

