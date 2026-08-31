"""ARC-AGI-3 fallback/portable MyAgent emitted by the true-scored-run notebook.

The notebook's Johnny5/TAAF execution plane is the primary scored path. This file
is also a valid ARC-AGI-3 Agent implementation and is emitted because official
starter notebooks conventionally expose `my_agent.py` beside `submission.parquet`.
"""
from __future__ import annotations

from typing import Any

from arcengine import FrameData, GameAction, GameState
from agents.agent import Agent
from multiverse_oracle.arcagi3 import ARCAGI3Policy, ARCPolicyConfig


class MyAgent(Agent):
    MAX_ACTIONS = 100000

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.policy = ARCAGI3Policy(
            ARCPolicyConfig(
                branch_count=96,
                horizon=5,
                seed=20260819,
                soft_stall=6,
                hard_stall=12,
                max_click_candidates=14,
                phantom_fail_closed_threshold=0.85,
                runtime_mechanics_enabled=True,
                runtime_probe_potential_reward=1.0,
                runtime_probe_action_cost=1.0,
                runtime_probe_failure_risk=0.15,
            )
        )

    @property
    def name(self) -> str:
        return f"{super().name}.johnny5_rdl_v2"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self,
        frames: list[FrameData],
        latest_frame: FrameData,
    ) -> GameAction:
        plan = self.policy.plan(latest_frame, fallback_game_id=self.game_id)
        action = GameAction.from_name(plan.action_name)
        if plan.data:
            action.set_data(dict(plan.data))
        action.reasoning = dict(plan.reasoning)
        return action
