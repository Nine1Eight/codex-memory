from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryCandidate:
    key: str
    value: Any
    game_ids: set[str] = field(default_factory=set)
    context_ids: set[str] = field(default_factory=set)
    successes: int = 0
    contradictions: int = 0


class QuarantinedMemory:
    def __init__(self, family_games: int = 2, universal_games: int = 3) -> None:
        self.family_games = family_games; self.universal_games = universal_games
        self.game: dict[str, dict[str, MemoryCandidate]] = {}
        self.family: dict[str, MemoryCandidate] = {}
        self.universal: dict[str, MemoryCandidate] = {}

    def observe(self, game_id: str, context_id: str, key: str, value: Any, success: bool) -> MemoryCandidate:
        candidate = self.game.setdefault(game_id, {}).setdefault(key, MemoryCandidate(key, value))
        candidate.game_ids.add(game_id); candidate.context_ids.add(context_id)
        if success: candidate.successes += 1
        else: candidate.contradictions += 1
        return candidate

    def propose_family(self, family: str, candidates: list[MemoryCandidate]) -> bool:
        games = set().union(*(item.game_ids for item in candidates)) if candidates else set()
        contexts = set().union(*(item.context_ids for item in candidates)) if candidates else set()
        if len(games) < self.family_games or len(contexts) < self.family_games or any(item.contradictions for item in candidates): return False
        merged = MemoryCandidate(candidates[0].key, candidates[0].value, games, contexts, sum(x.successes for x in candidates), 0)
        self.family[f"{family}:{merged.key}"] = merged; return True

    def propose_universal(self, family_keys: list[str]) -> bool:
        candidates = [self.family[key] for key in family_keys if key in self.family]
        games = set().union(*(item.game_ids for item in candidates)) if candidates else set()
        if len(games) < self.universal_games or len(candidates) < 2: return False
        key = candidates[0].key
        self.universal[key] = MemoryCandidate(key, candidates[0].value, games, set().union(*(x.context_ids for x in candidates)), sum(x.successes for x in candidates), 0)
        return True

