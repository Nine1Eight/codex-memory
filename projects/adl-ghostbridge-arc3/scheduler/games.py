from __future__ import annotations
class GameScheduler:
    def __init__(self, game_ids): self.remaining = list(dict.fromkeys(game_ids))
    def select_next_game(self) -> str:
        if not self.remaining: raise StopIteration
        return self.remaining.pop(0)
    def has_games(self) -> bool: return bool(self.remaining)
