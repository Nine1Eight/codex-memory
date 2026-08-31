import random
from arcengine import GameAction, GameState
from ..agent import Agent

class Random(Agent):
    MAX_ACTIONS = 80

    def is_done(self, frames, latest_frame):
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame):
        if latest_frame.state in [GameState.NOT_PLAYED, GameState.GAME_OVER]:
            return GameAction.RESET
        actions = [a for a in GameAction if a is not GameAction.RESET]
        return random.choice(actions)
