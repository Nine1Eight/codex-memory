from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .macro_compiler import GuardedMacro


@dataclass(frozen=True, slots=True)
class MacroResult:
    completed: bool
    actions_executed: int
    aborted_reason: str = ""


class MacroExecutor:
    def execute(self, macro: GuardedMacro, state: Any, execute_action: Callable[[Any], Any], observe_state: Callable[[], Any]) -> MacroResult:
        executed = 0
        for index, action in enumerate(macro.actions):
            if not all(check(state) for check in macro.preconditions):
                return MacroResult(False, executed, f"precondition failed before step {index}")
            execute_action(action); executed += 1; state = observe_state()
            if index < len(macro.postconditions) and not macro.postconditions[index](state):
                return MacroResult(False, executed, f"postcondition failed after step {index}")
        return MacroResult(True, executed)

