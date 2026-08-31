"""
Robust ARC-style procedural grid environment.

Design goals:
- No global RNG mutation.
- Layered state: background + independent entities.
- Subclass-safe action dispatch.
- Gymnasium-compatible reset/step signatures when Gymnasium is installed.
- Explicit termination/truncation/success/failure semantics.
- Variable grid sizes with optional observation padding.
- Support for movement, interaction, click-like actions, object collection, and Sokoban-style pushing.
- Lightweight vector wrapper for local curriculum rollouts.

The base class is intentionally generic. Subclasses should override _generate_world,
_check_goal, and optional hooks such as _on_enter_cell, _on_interact, and _on_click.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import copy
import math
import time

import numpy as np

try:  # Optional dependency; the env still works without gymnasium installed.
    import gymnasium as gym
    from gymnasium import spaces
except Exception:  # pragma: no cover - exact import failure depends on runtime.
    gym = None
    spaces = None


GridArray = np.ndarray
CoordTuple = Tuple[int, int]
InfoDict = Dict[str, Any]


class Action(IntEnum):
    """Six-action ARC-like control surface."""

    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    INTERACT = 4
    CLICK = 5


ACTION_DELTAS: Mapping[Action, CoordTuple] = {
    Action.UP: (-1, 0),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.RIGHT: (0, 1),
}


@dataclass(frozen=True, order=True)
class Position:
    """Immutable row/column coordinate."""

    row: int
    col: int

    def moved(self, delta: CoordTuple) -> "Position":
        return Position(self.row + int(delta[0]), self.col + int(delta[1]))

    def as_tuple(self) -> CoordTuple:
        return (self.row, self.col)

    @staticmethod
    def from_any(value: Union["Position", Sequence[int], np.ndarray]) -> "Position":
        if isinstance(value, Position):
            return value
        if isinstance(value, np.ndarray):
            if value.shape[0] != 2:
                raise ValueError(f"Position array must have length 2, got shape={value.shape}.")
            return Position(int(value[0]), int(value[1]))
        if len(value) != 2:  # type: ignore[arg-type]
            raise ValueError(f"Position sequence must have length 2, got {value!r}.")
        return Position(int(value[0]), int(value[1]))  # type: ignore[index]


@dataclass
class Entity:
    """Logical object that is rendered onto the grid without mutating background."""

    entity_id: str
    kind: str
    pos: Position
    color: int
    blocks: bool = False
    visible: bool = True
    pushable: bool = False
    collectible: bool = False
    alive: bool = True
    z_index: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "Entity":
        return Entity(
            entity_id=self.entity_id,
            kind=self.kind,
            pos=self.pos,
            color=int(self.color),
            blocks=bool(self.blocks),
            visible=bool(self.visible),
            pushable=bool(self.pushable),
            collectible=bool(self.collectible),
            alive=bool(self.alive),
            z_index=int(self.z_index),
            metadata=copy.deepcopy(self.metadata),
        )


@dataclass(frozen=True)
class ActionRequest:
    """Action plus optional pointer target for click-style tasks."""

    action: Union[int, Action]
    target: Optional[Union[Position, Sequence[int], np.ndarray]] = None


@dataclass(frozen=True)
class GoalStatus:
    """Result of goal checking."""

    terminated: bool
    success: bool = False
    failure: bool = False
    reason: str = ""
    reward_delta: float = 0.0

    @staticmethod
    def unfinished() -> "GoalStatus":
        return GoalStatus(terminated=False, success=False, failure=False, reason="unfinished", reward_delta=0.0)

    @staticmethod
    def solved(reason: str = "solved", reward_delta: float = 1.0) -> "GoalStatus":
        return GoalStatus(terminated=True, success=True, failure=False, reason=reason, reward_delta=reward_delta)

    @staticmethod
    def failed(reason: str = "failed", reward_delta: float = -1.0) -> "GoalStatus":
        return GoalStatus(terminated=True, success=False, failure=True, reason=reason, reward_delta=reward_delta)


@dataclass
class RewardConfig:
    """Reward shaping values used by the base class."""

    step_penalty: float = -0.01
    invalid_action_penalty: float = -0.05
    blocked_move_penalty: float = -0.02
    push_reward: float = 0.0
    collect_reward: float = 0.1
    interact_reward: float = 0.0
    click_reward: float = 0.0
    timeout_penalty: float = -1.0
    success_reward: float = 1.0
    failure_penalty: float = -1.0


class ARCGridEnv(gym.Env if gym is not None else object):
    """
    Subclass-safe ARC-style environment.

    Subclassing contract:
    - Override _generate_world(self, options) and call self.set_background,
      self.set_agent, and self.add_entity as needed.
    - Override _check_goal(self) and return GoalStatus.
    - Optional hooks:
      * _pre_step(request, action, target, info)
      * _post_step(request, action, target, reward, info)
      * _on_enter_cell(old_pos, new_pos, entities, info)
      * _on_interact(info)
      * _on_click(target, info)

    reset returns (observation, info). step returns
    (observation, reward, terminated, truncated, info), matching Gymnasium.
    """

    metadata = {"render_modes": ["ansi", "rgb_array", "grid"], "render_fps": 12}

    DEFAULT_PALETTE: Tuple[Tuple[int, int, int], ...] = (
        (0, 0, 0),
        (0, 116, 217),
        (46, 204, 64),
        (255, 65, 54),
        (255, 220, 0),
        (177, 13, 201),
        (255, 133, 27),
        (127, 219, 255),
        (57, 204, 204),
        (240, 18, 190),
        (1, 255, 112),
        (170, 170, 170),
        (133, 20, 75),
        (61, 153, 112),
        (255, 255, 255),
        (111, 111, 111),
    )

    def __init__(
        self,
        height: int = 64,
        width: int = 64,
        *,
        max_steps: int = 300,
        color_count: int = 16,
        obs_mode: str = "grid",
        partial_view: Optional[Union[int, Tuple[int, int]]] = None,
        pad_to: Optional[Tuple[int, int]] = None,
        seed: Optional[int] = None,
        reward_config: Optional[RewardConfig] = None,
        render_mode: Optional[str] = None,
        click_requires_target: bool = False,
        dtype: np.dtype = np.uint8,
    ) -> None:
        self.height = self._validate_positive_int(height, "height")
        self.width = self._validate_positive_int(width, "width")
        self.max_steps = self._validate_positive_int(max_steps, "max_steps")
        self.color_count = self._validate_positive_int(color_count, "color_count")
        if self.color_count > 256:
            raise ValueError("color_count must be <= 256 for uint-like grid rendering.")
        self.obs_mode = self._validate_obs_mode(obs_mode)
        self.partial_view = self._normalize_partial_view(partial_view)
        self.pad_to = self._normalize_pad_to(pad_to)
        self.render_mode = render_mode
        self.click_requires_target = bool(click_requires_target)
        self.dtype = np.dtype(dtype)
        if not np.issubdtype(self.dtype, np.integer):
            raise TypeError("dtype must be an integer dtype.")
        self.reward_config = reward_config or RewardConfig()

        self._initial_seed = seed
        self.rng = np.random.default_rng(seed)
        self.background: GridArray = np.zeros((self.height, self.width), dtype=self.dtype)
        self.entities: Dict[str, Entity] = {}
        self.agent_id: str = "agent"
        self.step_count: int = 0
        self.episode_id: int = 0
        self.terminated: bool = False
        self.truncated: bool = False
        self.last_info: InfoDict = {}
        self.history: List[InfoDict] = []
        self.created_at: float = time.time()

        self.action_space = spaces.Discrete(len(Action)) if spaces is not None else None
        self.observation_space = self._build_observation_space() if spaces is not None else None

    @staticmethod
    def _validate_positive_int(value: int, name: str) -> int:
        ivalue = int(value)
        if ivalue <= 0:
            raise ValueError(f"{name} must be positive, got {value!r}.")
        return ivalue

    @staticmethod
    def _validate_obs_mode(value: str) -> str:
        valid = {"grid", "channels", "normalized"}
        if value not in valid:
            raise ValueError(f"obs_mode must be one of {sorted(valid)}, got {value!r}.")
        return value

    @staticmethod
    def _normalize_partial_view(value: Optional[Union[int, Tuple[int, int]]]) -> Optional[Tuple[int, int]]:
        if value is None:
            return None
        if isinstance(value, int):
            h = w = int(value)
        else:
            h, w = int(value[0]), int(value[1])
        if h <= 0 or w <= 0:
            raise ValueError("partial_view dimensions must be positive.")
        if h % 2 == 0 or w % 2 == 0:
            raise ValueError("partial_view dimensions must be odd so the agent can be centered.")
        return (h, w)

    def _normalize_pad_to(self, value: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        if value is None:
            return None
        ph, pw = int(value[0]), int(value[1])
        if ph < self.height or pw < self.width:
            raise ValueError(f"pad_to={value!r} must be at least current size {(self.height, self.width)}.")
        return (ph, pw)

    def _build_observation_space(self) -> Any:
        if spaces is None:
            return None
        h, w = self._observation_hw()
        if self.obs_mode == "grid":
            return spaces.Box(low=0, high=self.color_count - 1, shape=(h, w), dtype=self.dtype)
        if self.obs_mode == "normalized":
            return spaces.Box(low=0.0, high=1.0, shape=(h, w), dtype=np.float32)
        return spaces.Box(low=0, high=1, shape=(self.color_count, h, w), dtype=np.uint8)

    def _observation_hw(self) -> Tuple[int, int]:
        if self.partial_view is not None:
            return self.partial_view
        if self.pad_to is not None:
            return self.pad_to
        return (self.height, self.width)

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[GridArray, InfoDict]:
        if seed is not None:
            self.rng = np.random.default_rng(int(seed))
        self.episode_id += 1
        self.step_count = 0
        self.terminated = False
        self.truncated = False
        self.entities = {}
        self.agent_id = "agent"
        self.background = np.zeros((self.height, self.width), dtype=self.dtype)
        self.history = []
        self.last_info = {
            "episode_id": self.episode_id,
            "seed_supplied": seed,
            "reset_options": dict(options or {}),
        }
        self._generate_world(dict(options or {}))
        self._validate_world_after_generation()
        obs = self.get_observation()
        info = self._base_info()
        info.update({"event": "reset"})
        self.last_info = info
        return obs, info

    def step(
        self,
        action_input: Union[int, Action, ActionRequest, Tuple[Union[int, Action], Any], Mapping[str, Any]],
    ) -> Tuple[GridArray, float, bool, bool, InfoDict]:
        if self.terminated or self.truncated:
            raise RuntimeError("Cannot call step() after episode ended. Call reset() first.")

        request = self._parse_action_request(action_input)
        action = self._validate_action(request.action)
        target = self._parse_target(request.target)
        info = self._base_info()
        info.update(
            {
                "action": int(action),
                "action_name": action.name,
                "target": None if target is None else target.as_tuple(),
                "events": [],
            }
        )

        self._pre_step(request, action, target, info)

        reward = float(self.reward_config.step_penalty)
        dispatch: Mapping[Action, Callable[[Optional[Position], InfoDict], float]] = {
            Action.UP: lambda _target, _info: self._move_agent(ACTION_DELTAS[Action.UP], _info),
            Action.DOWN: lambda _target, _info: self._move_agent(ACTION_DELTAS[Action.DOWN], _info),
            Action.LEFT: lambda _target, _info: self._move_agent(ACTION_DELTAS[Action.LEFT], _info),
            Action.RIGHT: lambda _target, _info: self._move_agent(ACTION_DELTAS[Action.RIGHT], _info),
            Action.INTERACT: lambda _target, _info: self._on_interact(_info),
            Action.CLICK: lambda _target, _info: self._click_dispatch(_target, _info),
        }
        reward += float(dispatch[action](target, info))

        self.step_count += 1
        goal_status = self._check_goal()
        if goal_status.terminated:
            self.terminated = True
            info["goal_reason"] = goal_status.reason
            info["success"] = bool(goal_status.success)
            info["failure"] = bool(goal_status.failure)
            if goal_status.success:
                reward += float(self.reward_config.success_reward)
            if goal_status.failure:
                reward += float(self.reward_config.failure_penalty)
            reward += float(goal_status.reward_delta)
        elif self.step_count >= self.max_steps:
            self.truncated = True
            reward += float(self.reward_config.timeout_penalty)
            info["goal_reason"] = "timeout"
            info["success"] = False
            info["failure"] = True
        else:
            info["goal_reason"] = goal_status.reason
            info["success"] = False
            info["failure"] = False

        self._post_step(request, action, target, reward, info)
        obs = self.get_observation()
        info.update(
            {
                "step_count": self.step_count,
                "terminated": self.terminated,
                "truncated": self.truncated,
                "reward": float(reward),
                "agent_pos": self.agent.pos.as_tuple(),
            }
        )
        self.last_info = copy.deepcopy(info)
        self.history.append(copy.deepcopy(info))
        return obs, float(reward), bool(self.terminated), bool(self.truncated), info

    def _parse_action_request(
        self,
        action_input: Union[int, Action, ActionRequest, Tuple[Union[int, Action], Any], Mapping[str, Any]],
    ) -> ActionRequest:
        if isinstance(action_input, ActionRequest):
            return action_input
        if isinstance(action_input, Mapping):
            if "action" not in action_input:
                raise ValueError("Action mapping must include an 'action' key.")
            return ActionRequest(action=action_input["action"], target=action_input.get("target"))
        if isinstance(action_input, tuple):
            if len(action_input) != 2:
                raise ValueError("Tuple action input must be (action, target).")
            return ActionRequest(action=action_input[0], target=action_input[1])
        return ActionRequest(action=action_input, target=None)

    def _validate_action(self, action: Union[int, Action]) -> Action:
        try:
            parsed = Action(int(action))
        except Exception as exc:
            raise ValueError(f"Invalid action {action!r}. Valid values are 0 through {len(Action) - 1}.") from exc
        return parsed

    def _parse_target(self, target: Optional[Union[Position, Sequence[int], np.ndarray]]) -> Optional[Position]:
        if target is None:
            return None
        pos = Position.from_any(target)
        if not self.in_bounds(pos):
            raise ValueError(f"target coordinate {pos.as_tuple()} is outside grid size {(self.height, self.width)}.")
        return pos

    def _click_dispatch(self, target: Optional[Position], info: InfoDict) -> float:
        if target is None:
            if self.click_requires_target:
                info["events"].append("missing_click_target")
                return float(self.reward_config.invalid_action_penalty)
            target = self.agent.pos
        return float(self._on_click(target, info))

    def _move_agent(self, delta: CoordTuple, info: InfoDict) -> float:
        old_pos = self.agent.pos
        new_pos = old_pos.moved(delta)
        if not self.in_bounds(new_pos):
            info["events"].append("move_out_of_bounds")
            return float(self.reward_config.invalid_action_penalty)

        blockers = self.entities_at(new_pos, alive_only=True, visible_only=False, blocks_only=True)
        if blockers:
            if len(blockers) == 1 and blockers[0].pushable:
                pushed = self._try_push(blockers[0], delta, info)
                if not pushed:
                    info["events"].append("push_blocked")
                    return float(self.reward_config.blocked_move_penalty)
                self.agent.pos = new_pos
                info["events"].append("push")
                reward = float(self.reward_config.push_reward)
                reward += float(self._on_enter_cell(old_pos, new_pos, self.entities_at(new_pos), info))
                return reward
            info["events"].append("move_blocked")
            return float(self.reward_config.blocked_move_penalty)

        self.agent.pos = new_pos
        info["events"].append("move")
        return float(self._on_enter_cell(old_pos, new_pos, self.entities_at(new_pos), info))

    def _try_push(self, entity: Entity, delta: CoordTuple, info: InfoDict) -> bool:
        destination = entity.pos.moved(delta)
        if not self.in_bounds(destination):
            return False
        blockers = [e for e in self.entities_at(destination, alive_only=True, visible_only=False, blocks_only=True) if e.entity_id != entity.entity_id]
        if blockers:
            return False
        entity.pos = destination
        info.setdefault("pushed", []).append({"entity_id": entity.entity_id, "to": destination.as_tuple()})
        return True

    def _on_enter_cell(self, old_pos: Position, new_pos: Position, entities: Sequence[Entity], info: InfoDict) -> float:
        reward = 0.0
        for entity in list(entities):
            if entity.entity_id == self.agent_id or not entity.alive:
                continue
            if entity.collectible:
                entity.alive = False
                entity.visible = False
                info["events"].append("collect")
                info.setdefault("collected", []).append(entity.entity_id)
                reward += float(self.reward_config.collect_reward)
        return reward

    def _on_interact(self, info: InfoDict) -> float:
        info["events"].append("interact")
        return float(self.reward_config.interact_reward)

    def _on_click(self, target: Position, info: InfoDict) -> float:
        info["events"].append("click")
        info["clicked_cell"] = target.as_tuple()
        return float(self.reward_config.click_reward)

    def _pre_step(self, request: ActionRequest, action: Action, target: Optional[Position], info: InfoDict) -> None:
        return None

    def _post_step(self, request: ActionRequest, action: Action, target: Optional[Position], reward: float, info: InfoDict) -> None:
        return None

    def _generate_world(self, options: MutableMapping[str, Any]) -> None:
        """
        Default world: a clear grid with an agent at top-left and target at bottom-right.
        Subclasses should replace this with procedural generation.
        """
        self.set_background(np.zeros((self.height, self.width), dtype=self.dtype))
        self.set_agent(Position(0, 0), color=1)
        self.add_entity(Entity("target", "target", Position(self.height - 1, self.width - 1), color=2, blocks=False, z_index=5))

    def _check_goal(self) -> GoalStatus:
        target = self.entities.get("target")
        if target is not None and target.alive and self.agent.pos == target.pos:
            return GoalStatus.solved("agent_reached_target", reward_delta=0.0)
        return GoalStatus.unfinished()

    def _validate_world_after_generation(self) -> None:
        if self.agent_id not in self.entities:
            raise RuntimeError("World generation must create an agent via set_agent().")
        if self.background.shape != (self.height, self.width):
            raise RuntimeError(f"background shape must be {(self.height, self.width)}, got {self.background.shape}.")
        if np.min(self.background) < 0 or np.max(self.background) >= self.color_count:
            raise ValueError(f"background colors must be in [0, {self.color_count - 1}].")
        seen: set[str] = set()
        for entity_id, entity in self.entities.items():
            if entity_id != entity.entity_id:
                raise RuntimeError(f"Entity dictionary key {entity_id!r} does not match entity_id {entity.entity_id!r}.")
            if entity_id in seen:
                raise RuntimeError(f"Duplicate entity_id {entity_id!r}.")
            seen.add(entity_id)
            if not self.in_bounds(entity.pos):
                raise ValueError(f"Entity {entity_id!r} has out-of-bounds position {entity.pos.as_tuple()}.")
            if entity.color < 0 or entity.color >= self.color_count:
                raise ValueError(f"Entity {entity_id!r} color {entity.color} outside [0, {self.color_count - 1}].")

    @property
    def agent(self) -> Entity:
        try:
            return self.entities[self.agent_id]
        except KeyError as exc:
            raise RuntimeError("Agent has not been created. Call reset() or set_agent().") from exc

    def set_background(self, grid: Union[GridArray, Sequence[Sequence[int]]]) -> None:
        arr = np.asarray(grid, dtype=self.dtype)
        if arr.shape != (self.height, self.width):
            raise ValueError(f"background must have shape {(self.height, self.width)}, got {arr.shape}.")
        if arr.size and (int(arr.min()) < 0 or int(arr.max()) >= self.color_count):
            raise ValueError(f"background colors must be in [0, {self.color_count - 1}].")
        self.background = arr.copy()

    def set_agent(self, pos: Union[Position, Sequence[int], np.ndarray], *, color: int = 1, entity_id: str = "agent", **metadata: Any) -> Entity:
        position = Position.from_any(pos)
        if not self.in_bounds(position):
            raise ValueError(f"Agent position {position.as_tuple()} is out of bounds.")
        self.agent_id = entity_id
        entity = Entity(
            entity_id=entity_id,
            kind="agent",
            pos=position,
            color=int(color),
            blocks=False,
            visible=True,
            pushable=False,
            collectible=False,
            alive=True,
            z_index=100,
            metadata=dict(metadata),
        )
        self.add_entity(entity, replace=True)
        return entity

    def add_entity(self, entity: Entity, *, replace: bool = False) -> Entity:
        if entity.entity_id in self.entities and not replace:
            raise ValueError(f"Entity {entity.entity_id!r} already exists. Pass replace=True to overwrite.")
        if not self.in_bounds(entity.pos):
            raise ValueError(f"Entity {entity.entity_id!r} position {entity.pos.as_tuple()} is out of bounds.")
        if entity.color < 0 or entity.color >= self.color_count:
            raise ValueError(f"Entity color must be in [0, {self.color_count - 1}], got {entity.color}.")
        self.entities[entity.entity_id] = entity
        return entity

    def remove_entity(self, entity_id: str) -> Entity:
        if entity_id == self.agent_id:
            raise ValueError("Cannot remove the active agent with remove_entity().")
        try:
            return self.entities.pop(entity_id)
        except KeyError as exc:
            raise KeyError(f"No entity with id {entity_id!r}.") from exc

    def in_bounds(self, pos: Union[Position, Sequence[int], np.ndarray]) -> bool:
        p = Position.from_any(pos)
        return 0 <= p.row < self.height and 0 <= p.col < self.width

    def entities_at(
        self,
        pos: Union[Position, Sequence[int], np.ndarray],
        *,
        alive_only: bool = True,
        visible_only: bool = False,
        blocks_only: bool = False,
        exclude_agent: bool = False,
    ) -> List[Entity]:
        p = Position.from_any(pos)
        found: List[Entity] = []
        for entity in self.entities.values():
            if entity.pos != p:
                continue
            if alive_only and not entity.alive:
                continue
            if visible_only and not entity.visible:
                continue
            if blocks_only and not entity.blocks:
                continue
            if exclude_agent and entity.entity_id == self.agent_id:
                continue
            found.append(entity)
        found.sort(key=lambda e: (e.z_index, e.entity_id))
        return found

    def occupancy(self, *, blocks_only: bool = True) -> Dict[CoordTuple, List[str]]:
        occ: Dict[CoordTuple, List[str]] = {}
        for entity in self.entities.values():
            if not entity.alive:
                continue
            if blocks_only and not entity.blocks:
                continue
            occ.setdefault(entity.pos.as_tuple(), []).append(entity.entity_id)
        return occ

    def compose_grid(self, *, include_hidden: bool = False) -> GridArray:
        grid = self.background.copy()
        ordered = sorted(self.entities.values(), key=lambda e: (e.z_index, e.entity_id))
        for entity in ordered:
            if not entity.alive:
                continue
            if not entity.visible and not include_hidden:
                continue
            if self.in_bounds(entity.pos):
                grid[entity.pos.row, entity.pos.col] = np.asarray(entity.color, dtype=self.dtype)
        return grid

    def get_observation(self) -> GridArray:
        grid = self.compose_grid()
        if self.partial_view is not None:
            grid = self._extract_partial_view(grid)
        elif self.pad_to is not None:
            grid = self._pad_grid(grid, self.pad_to, fill=0)

        if self.obs_mode == "grid":
            return grid.copy()
        if self.obs_mode == "normalized":
            denom = float(max(1, self.color_count - 1))
            return (grid.astype(np.float32) / denom).copy()
        return self._one_hot(grid).copy()

    def _extract_partial_view(self, grid: GridArray) -> GridArray:
        if self.partial_view is None:
            return grid
        ph, pw = self.partial_view
        ar, ac = self.agent.pos.row, self.agent.pos.col
        radius_h = ph // 2
        radius_w = pw // 2
        padded = np.pad(grid, ((radius_h, radius_h), (radius_w, radius_w)), mode="constant", constant_values=0)
        pr = ar + radius_h
        pc = ac + radius_w
        return padded[pr - radius_h : pr + radius_h + 1, pc - radius_w : pc + radius_w + 1]

    @staticmethod
    def _pad_grid(grid: GridArray, target_shape: Tuple[int, int], fill: int = 0) -> GridArray:
        th, tw = int(target_shape[0]), int(target_shape[1])
        if grid.shape[0] > th or grid.shape[1] > tw:
            raise ValueError(f"Cannot pad grid shape={grid.shape} to smaller target_shape={target_shape}.")
        out = np.full((th, tw), fill, dtype=grid.dtype)
        out[: grid.shape[0], : grid.shape[1]] = grid
        return out

    def _one_hot(self, grid: GridArray) -> GridArray:
        if grid.size and (int(grid.min()) < 0 or int(grid.max()) >= self.color_count):
            raise ValueError("Grid contains values outside valid color range.")
        return np.eye(self.color_count, dtype=np.uint8)[grid.astype(np.int64)].transpose(2, 0, 1)

    def render(self, mode: Optional[str] = None) -> Union[str, GridArray]:
        resolved = mode or self.render_mode or "ansi"
        grid = self.compose_grid()
        if resolved == "grid":
            return grid
        if resolved == "ansi":
            return self._render_ansi(grid)
        if resolved == "rgb_array":
            return self._render_rgb(grid)
        raise ValueError(f"Unsupported render mode {resolved!r}.")

    def _render_ansi(self, grid: GridArray) -> str:
        chars = "0123456789ABCDEF"
        lines: List[str] = []
        for row in grid:
            line = "".join(chars[int(v)] if 0 <= int(v) < len(chars) else "?" for v in row)
            lines.append(line)
        return "\n".join(lines)

    def _render_rgb(self, grid: GridArray) -> GridArray:
        palette = np.asarray(self.DEFAULT_PALETTE[: self.color_count], dtype=np.uint8)
        if len(palette) < self.color_count:
            extra_count = self.color_count - len(palette)
            extra = self.rng.integers(0, 256, size=(extra_count, 3), dtype=np.uint8)
            palette = np.vstack([palette, extra])
        return palette[grid.astype(np.int64)]

    def clone_state(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "width": self.width,
            "background": self.background.copy(),
            "entities": {k: v.clone() for k, v in self.entities.items()},
            "agent_id": self.agent_id,
            "step_count": self.step_count,
            "episode_id": self.episode_id,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "rng_state": copy.deepcopy(self.rng.bit_generator.state),
            "last_info": copy.deepcopy(self.last_info),
            "history": copy.deepcopy(self.history),
        }

    def restore_state(self, state: Mapping[str, Any]) -> None:
        if int(state["height"]) != self.height or int(state["width"]) != self.width:
            raise ValueError("Cannot restore state with different grid dimensions.")
        self.background = np.asarray(state["background"], dtype=self.dtype).copy()
        self.entities = {str(k): v.clone() for k, v in state["entities"].items()}
        self.agent_id = str(state["agent_id"])
        self.step_count = int(state["step_count"])
        self.episode_id = int(state["episode_id"])
        self.terminated = bool(state["terminated"])
        self.truncated = bool(state["truncated"])
        self.rng.bit_generator.state = copy.deepcopy(state["rng_state"])
        self.last_info = copy.deepcopy(state["last_info"])
        self.history = copy.deepcopy(state["history"])
        self._validate_world_after_generation()

    def shortest_path_to(
        self,
        target: Union[Position, Sequence[int], np.ndarray],
        *,
        avoid_blockers: bool = True,
        max_nodes: Optional[int] = None,
    ) -> Optional[List[Action]]:
        """Small BFS utility for debugging curricula and imitation targets."""
        goal = Position.from_any(target)
        if not self.in_bounds(goal):
            raise ValueError(f"Target {goal.as_tuple()} out of bounds.")
        start = self.agent.pos
        if start == goal:
            return []
        blocked: set[CoordTuple] = set()
        if avoid_blockers:
            for entity in self.entities.values():
                if entity.alive and entity.blocks and entity.entity_id != self.agent_id:
                    blocked.add(entity.pos.as_tuple())
        frontier: List[Position] = [start]
        came_from: Dict[Position, Tuple[Position, Action]] = {}
        visited = {start}
        nodes = 0
        while frontier:
            current = frontier.pop(0)
            nodes += 1
            if max_nodes is not None and nodes > max_nodes:
                return None
            for action, delta in ACTION_DELTAS.items():
                nxt = current.moved(delta)
                if not self.in_bounds(nxt):
                    continue
                if nxt.as_tuple() in blocked:
                    continue
                if nxt in visited:
                    continue
                visited.add(nxt)
                came_from[nxt] = (current, action)
                if nxt == goal:
                    path: List[Action] = []
                    cursor = goal
                    while cursor != start:
                        prev, act = came_from[cursor]
                        path.append(act)
                        cursor = prev
                    path.reverse()
                    return path
                frontier.append(nxt)
        return None

    def _base_info(self) -> InfoDict:
        return {
            "episode_id": self.episode_id,
            "step_count": self.step_count,
            "max_steps": self.max_steps,
            "grid_shape": (self.height, self.width),
            "agent_id": self.agent_id,
            "agent_pos": self.agent.pos.as_tuple() if self.agent_id in self.entities else None,
        }


class KeyDoorEnv(ARCGridEnv):
    """
    Procedural key-door-target task.

    Colors:
    - 0 background
    - 1 agent
    - 2 target
    - 3 wall
    - 4 key
    - 5 locked door
    """

    def __init__(self, *args: Any, wall_density: float = 0.08, **kwargs: Any) -> None:
        self.wall_density = float(wall_density)
        if not (0.0 <= self.wall_density <= 0.35):
            raise ValueError("wall_density must be in [0.0, 0.35].")
        super().__init__(*args, **kwargs)

    def _generate_world(self, options: MutableMapping[str, Any]) -> None:
        self.set_background(np.zeros((self.height, self.width), dtype=self.dtype))
        required = max(6, min(self.height * self.width, 6))
        if self.height * self.width < required:
            raise ValueError("KeyDoorEnv needs at least 6 cells.")

        positions = self._sample_unique_positions(5)
        agent_pos, key_pos, door_pos, target_pos, reserved = positions
        self.set_agent(agent_pos, color=1, has_key=False)
        self.add_entity(Entity("key", "key", key_pos, color=4, blocks=False, collectible=True, z_index=20))
        self.add_entity(Entity("door", "door", door_pos, color=5, blocks=True, z_index=20, metadata={"locked": True}))
        self.add_entity(Entity("target", "target", target_pos, color=2, blocks=False, z_index=10))

        wall_budget = int(round(self.height * self.width * self.wall_density))
        protected = {agent_pos, key_pos, door_pos, target_pos, reserved}
        for idx in range(wall_budget):
            pos = self._sample_free_position(protected=protected)
            protected.add(pos)
            self.add_entity(Entity(f"wall_{idx}", "wall", pos, color=3, blocks=True, z_index=15))

    def _sample_unique_positions(self, count: int) -> List[Position]:
        total = self.height * self.width
        if count > total:
            raise ValueError(f"Cannot sample {count} positions from {total} cells.")
        flat = self.rng.choice(total, size=count, replace=False)
        return [Position(int(v // self.width), int(v % self.width)) for v in flat]

    def _sample_free_position(self, *, protected: Iterable[Position]) -> Position:
        protected_set = set(protected)
        for _ in range(max(100, self.height * self.width * 2)):
            pos = Position(int(self.rng.integers(0, self.height)), int(self.rng.integers(0, self.width)))
            if pos not in protected_set and not self.entities_at(pos, alive_only=True):
                return pos
        for r in range(self.height):
            for c in range(self.width):
                pos = Position(r, c)
                if pos not in protected_set and not self.entities_at(pos, alive_only=True):
                    return pos
        raise RuntimeError("No free position available.")

    def _on_enter_cell(self, old_pos: Position, new_pos: Position, entities: Sequence[Entity], info: InfoDict) -> float:
        reward = super()._on_enter_cell(old_pos, new_pos, entities, info)
        if "key" in info.get("collected", []):
            self.agent.metadata["has_key"] = True
            info["events"].append("has_key")
        return reward

    def _on_interact(self, info: InfoDict) -> float:
        reward = float(self.reward_config.interact_reward)
        has_key = bool(self.agent.metadata.get("has_key", False))
        adjacent = [self.agent.pos.moved(delta) for delta in ACTION_DELTAS.values()]
        for pos in adjacent:
            if not self.in_bounds(pos):
                continue
            for entity in self.entities_at(pos, alive_only=True, visible_only=False):
                if entity.kind == "door" and entity.metadata.get("locked", True):
                    if has_key:
                        entity.metadata["locked"] = False
                        entity.blocks = False
                        entity.color = 6 if self.color_count > 6 else entity.color
                        info["events"].append("unlock_door")
                        return reward + 0.2
                    info["events"].append("door_locked_no_key")
                    return reward + float(self.reward_config.blocked_move_penalty)
        info["events"].append("interact_nothing")
        return reward

    def _check_goal(self) -> GoalStatus:
        target = self.entities.get("target")
        if target is not None and target.alive and self.agent.pos == target.pos:
            return GoalStatus.solved("target_reached", reward_delta=0.0)
        return GoalStatus.unfinished()


class SokobanLiteEnv(ARCGridEnv):
    """
    Minimal Sokoban-like task for validating push-safe base mechanics.

    Colors:
    - 0 background
    - 1 agent
    - 2 goal
    - 3 wall
    - 7 box
    """

    def _generate_world(self, options: MutableMapping[str, Any]) -> None:
        self.set_background(np.zeros((self.height, self.width), dtype=self.dtype))
        if self.height < 5 or self.width < 5:
            raise ValueError("SokobanLiteEnv needs at least a 5x5 grid.")
        for r in range(self.height):
            self.add_entity(Entity(f"wall_l_{r}", "wall", Position(r, 0), color=3, blocks=True, z_index=15))
            self.add_entity(Entity(f"wall_r_{r}", "wall", Position(r, self.width - 1), color=3, blocks=True, z_index=15))
        for c in range(1, self.width - 1):
            self.add_entity(Entity(f"wall_t_{c}", "wall", Position(0, c), color=3, blocks=True, z_index=15))
            self.add_entity(Entity(f"wall_b_{c}", "wall", Position(self.height - 1, c), color=3, blocks=True, z_index=15))

        mid_r = self.height // 2
        mid_c = self.width // 2
        self.set_agent(Position(mid_r, max(1, mid_c - 1)), color=1)
        self.add_entity(Entity("box", "box", Position(mid_r, mid_c), color=7, blocks=True, pushable=True, z_index=20))
        self.add_entity(Entity("goal", "goal", Position(mid_r, min(self.width - 2, mid_c + 2)), color=2, blocks=False, z_index=5))

    def _check_goal(self) -> GoalStatus:
        box = self.entities.get("box")
        goal = self.entities.get("goal")
        if box is not None and goal is not None and box.alive and goal.alive and box.pos == goal.pos:
            return GoalStatus.solved("box_on_goal", reward_delta=0.0)
        return GoalStatus.unfinished()


class SyncVectorARCEnv:
    """Simple synchronous vector wrapper for curriculum collection without external RL libs."""

    def __init__(self, env_fns: Sequence[Callable[[], ARCGridEnv]]) -> None:
        if not env_fns:
            raise ValueError("env_fns must contain at least one constructor.")
        self.envs = [fn() for fn in env_fns]
        self.num_envs = len(self.envs)

    def reset(self, seeds: Optional[Sequence[Optional[int]]] = None) -> Tuple[List[GridArray], List[InfoDict]]:
        if seeds is None:
            seeds = [None] * self.num_envs
        if len(seeds) != self.num_envs:
            raise ValueError(f"Expected {self.num_envs} seeds, got {len(seeds)}.")
        obs: List[GridArray] = []
        infos: List[InfoDict] = []
        for env, seed in zip(self.envs, seeds):
            o, info = env.reset(seed=seed)
            obs.append(o)
            infos.append(info)
        return obs, infos

    def step(
        self,
        actions: Sequence[Union[int, Action, ActionRequest, Tuple[Union[int, Action], Any], Mapping[str, Any]]],
        *,
        auto_reset: bool = False,
    ) -> Tuple[List[GridArray], np.ndarray, np.ndarray, np.ndarray, List[InfoDict]]:
        if len(actions) != self.num_envs:
            raise ValueError(f"Expected {self.num_envs} actions, got {len(actions)}.")
        obs: List[GridArray] = []
        rewards: List[float] = []
        terminated: List[bool] = []
        truncated: List[bool] = []
        infos: List[InfoDict] = []
        for env, action in zip(self.envs, actions):
            if auto_reset and (env.terminated or env.truncated):
                o, info = env.reset()
                info["auto_reset"] = True
                obs.append(o)
                rewards.append(0.0)
                terminated.append(False)
                truncated.append(False)
                infos.append(info)
                continue
            o, reward, term, trunc, info = env.step(action)
            obs.append(o)
            rewards.append(float(reward))
            terminated.append(bool(term))
            truncated.append(bool(trunc))
            infos.append(info)
        return obs, np.asarray(rewards, dtype=np.float32), np.asarray(terminated, dtype=bool), np.asarray(truncated, dtype=bool), infos

    def render(self, mode: str = "ansi") -> List[Union[str, GridArray]]:
        return [env.render(mode=mode) for env in self.envs]

    def close(self) -> None:
        self.envs.clear()


def smoke_test() -> Dict[str, Any]:
    """Deterministic sanity tests for the base environment and example subclasses."""
    base = ARCGridEnv(height=4, width=4, max_steps=20, seed=918)
    obs, info = base.reset(seed=918)
    assert obs.shape == (4, 4), obs.shape
    assert info["agent_pos"] == (0, 0), info
    path = base.shortest_path_to((3, 3))
    assert path is not None and len(path) == 6
    total_reward = 0.0
    terminated = False
    truncated = False
    for act in path:
        _, reward, terminated, truncated, info = base.step(act)
        total_reward += reward
        if terminated or truncated:
            break
    assert terminated and not truncated and info["success"] is True

    key_env = KeyDoorEnv(height=8, width=8, max_steps=50, seed=123, wall_density=0.0)
    key_obs, key_info = key_env.reset(seed=123)
    assert key_obs.shape == (8, 8)
    assert key_info["agent_pos"] == key_env.agent.pos.as_tuple()

    sokoban = SokobanLiteEnv(height=7, width=7, max_steps=20, seed=1)
    sokoban.reset(seed=1)
    _, reward, terminated, truncated, info = sokoban.step(Action.RIGHT)
    assert "push" in info["events"], info
    assert not terminated and not truncated

    vec = SyncVectorARCEnv([
        lambda: ARCGridEnv(height=4, width=4, seed=1),
        lambda: SokobanLiteEnv(height=7, width=7, seed=2),
    ])
    obs_list, info_list = vec.reset(seeds=[1, 2])
    assert len(obs_list) == 2 and len(info_list) == 2
    _, rewards, terms, truncs, infos = vec.step([Action.RIGHT, Action.RIGHT])
    assert rewards.shape == (2,) and terms.shape == (2,) and truncs.shape == (2,)

    return {
        "base_path_len": len(path),
        "base_total_reward": round(float(total_reward), 4),
        "keydoor_shape": tuple(key_obs.shape),
        "sokoban_events": info["events"],
        "vector_envs": vec.num_envs,
    }


if __name__ == "__main__":
    result = smoke_test()
    print(result)
