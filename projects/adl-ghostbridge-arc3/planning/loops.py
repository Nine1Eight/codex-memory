from __future__ import annotations

from collections import Counter, deque

from world.state import Action, Reflection, WorldState


class LoopGuard:
    def __init__(self, window: int = 12) -> None:
        self.states = deque(maxlen=window); self.actions = deque(maxlen=window); self.no_progress = 0; self.resets = 0

    def observe(self, world: WorldState, action: Action, reflection: Reflection) -> tuple[bool, str]:
        self.states.append(world.state_key); self.actions.append(action.key())
        self.no_progress = 0 if reflection.delta.progress_delta > 0 or world.level_complete else self.no_progress + 1
        if Counter(self.states).most_common(1)[0][1] >= 3: return True, "repeated_state_hash"
        if len(self.actions) >= 6 and tuple(self.actions)[-3:] == tuple(self.actions)[-6:-3]: return True, "repeated_action_sequence"
        if self.no_progress >= self.states.maxlen: return True, "no_progress_window"
        return False, ""


class ResetPolicy:
    def __init__(self) -> None: self.failures = 0

    def should_reset(self, world: WorldState, looped: bool, known_replay_value: float = 0.0) -> bool:
        if world.failed: self.failures += 1
        unrecoverable = world.failed and not world.game_complete and self.failures >= 1
        controlled_comparison = looped and self.failures < 3
        return unrecoverable or controlled_comparison or known_replay_value > 0.8
