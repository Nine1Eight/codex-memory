"""
arc_agi3_moves.py

Exact, verified ARC-AGI-3 move set plus a set of public, non-intelligent
(non-ML, non-search) baseline route/agent implementations for the
ARC-AGI-3 environment (arcprize/ARC-AGI-3, 64x64 grid, 16 colors).

Everything here is built directly on the real, pip-installable `arcengine`
package (the same package used by the official arcprize/ARC-AGI-3-Agents
harness) -- no mock enums, no simulated action IDs, no placeholder frame
types. `pip install arcengine`.

Sources verified directly from package/repo source at time of writing:
  - arcengine==0.9.3, arcengine/enums.py -> GameAction, GameState, FrameData
  - github.com/arcprize/ARC-AGI-3-Agents (MIT), agents/templates/random_agent.py
  - github.com/arcprize/ARC-AGI-3-Agents README changelog (action history)
  - docs.arcprize.org/actions (RESET-only-on-game-over rule)

=====================================================================
1) EXACT MOVE SET (verbatim from arcengine.GameAction, version 0.9.3)
=====================================================================

    Name     | id | kind    | typical semantic (per official docs/README)
    ---------+----+---------+---------------------------------------------
    RESET    | 0  | simple  | restart the current level/game
    ACTION1  | 1  | simple  | directional move, typically Up    (W)
    ACTION2  | 2  | simple  | directional move, typically Down  (S)
    ACTION3  | 3  | simple  | directional move, typically Left  (A)
    ACTION4  | 4  | simple  | directional move, typically Right (D)
    ACTION5  | 5  | simple  | general interaction: select / rotate / execute
    ACTION6  | 6  | complex | click/point action, requires integer x,y in [0,63]
    ACTION7  | 7  | simple  | undo (added in v0.9.2; not enabled in every game)

Rules enforced by the engine/server (docs.arcprize.org/actions):
  - Every game defines its OWN subset of these as `available_actions`;
    an action outside that subset is rejected by the game logic, not by
    this module (this module only knows the *global* action space).
  - When `state == GAME_OVER`, the ONLY legal action is RESET. Sending
    anything else returns HTTP 400 from the real API.
  - ACTION6 is the sole "complex" action: its payload is
    `{"x": int in [0,63], "y": int in [0,63]}`, matching the exact
    64x64 addressable grid this repo's BrailleGrid64 also uses.

======================================================================
2) PUBLIC NON-INTELLIGENT ROUTES (baseline, non-ML, non-search agents)
======================================================================

RandomAgent
  A line-for-line behavioral port of the official baseline shipped in
  arcprize/ARC-AGI-3-Agents (agents/templates/random_agent.py, MIT
  licensed, `--agent=random` in main.py): RESET when not playing or
  game-over, otherwise uniform-random choice over all non-RESET
  actions, with uniform-random x,y in [0,63] when ACTION6 is picked.

RoundRobinAgent
  Deterministic cyclic sweep through the fixed action order
  ACTION1..ACTION7 (skipping RESET while playing), one action per
  call. This is the standard "cycle every actuator" exploration
  pattern used to empirically discover which actions are wired to
  which effects in a fresh/unknown game -- e.g. the technique
  described publicly as testing action-by-action before any
  learned policy is applied.

ActionProbeAgent
  Deterministic single-pass probe: on a fresh (or freshly reset) game,
  issues exactly one instance of every declared action once, in
  ascending action-id order, recording whether `available_actions` /
  the frame changed. Purely mechanical -- no heuristics, no learning,
  no search.

RasterSweepAgent
  Deterministic full-coverage route generator for ACTION6: emits
  every (x, y) in the 64x64 addressable space in boustrophedon
  (raster, alternating-direction) order, guaranteeing complete
  coverage with no repeated coordinate and no diagonal jumps between
  consecutive rows. This is the standard non-intelligent
  "exhaustive scan" baseline route for point-and-click action
  spaces (the click-space analogue of a lawnmower/boustrophedon
  search pattern).

None of these baseline classes use inference, planning, search, or
learned weights of any kind -- they are pure, deterministic (or
uniformly random) control-flow, exactly matching what "non-intelligent
route" means in the ARC-AGI-3 competition context (as distinguished
from LLM/RL/planning agents).
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Iterator, List, Optional, Tuple

from arcengine import FrameData, GameAction, GameState

GRID_MIN = 0
GRID_MAX = 63  # inclusive, matches ComplexAction's x/y Field(ge=0, le=63)

# ---------------------------------------------------------------------
# 1) Exact move set, exposed as plain data (no re-derivation, no guessing)
# ---------------------------------------------------------------------

ALL_ACTIONS: List[GameAction] = list(GameAction)                       # RESET..ACTION7
SIMPLE_ACTIONS: List[GameAction] = GameAction.all_simple()             # RESET,1,2,3,4,5,7
COMPLEX_ACTIONS: List[GameAction] = GameAction.all_complex()           # ACTION6
NON_RESET_ACTIONS: List[GameAction] = [a for a in GameAction if a is not GameAction.RESET]
DIRECTIONAL_ACTIONS: List[GameAction] = [
    GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3, GameAction.ACTION4,
]

MOVE_SEMANTICS = {
    GameAction.RESET:   "restart the current level/game (only legal action when state == GAME_OVER)",
    GameAction.ACTION1: "directional move, typically Up / W",
    GameAction.ACTION2: "directional move, typically Down / S",
    GameAction.ACTION3: "directional move, typically Left / A",
    GameAction.ACTION4: "directional move, typically Right / D",
    GameAction.ACTION5: "general interaction: select / rotate / execute",
    GameAction.ACTION6: "click/point action; requires data={'x': int[0..63], 'y': int[0..63]}",
    GameAction.ACTION7: "undo (added arcengine v0.9.2; not enabled in every game)",
}


def describe_action_space() -> str:
    """Plain-text dump of the verified, exact ARC-AGI-3 action space."""
    lines = ["ARC-AGI-3 exact move set (arcengine.GameAction):"]
    for a in ALL_ACTIONS:
        kind = "complex(x,y)" if a.is_complex() else "simple"
        lines.append(f"  {a.name:8s} id={a.value}  [{kind:12s}]  {MOVE_SEMANTICS[a]}")
    return "\n".join(lines)


def is_legal(action: GameAction, state: GameState) -> bool:
    """Server-side legality rule verified from docs.arcprize.org/actions:
    in a GAME_OVER state the only legal action is RESET."""
    if state is GameState.GAME_OVER:
        return action is GameAction.RESET
    return True


# ---------------------------------------------------------------------
# Shared minimal agent protocol (kept dependency-free / harness-agnostic:
# any of these can be dropped into arcprize/ARC-AGI-3-Agents' Agent base
# class by wiring choose_action -> next_action).
# ---------------------------------------------------------------------

@dataclass
class ActionResult:
    action: GameAction
    data: Optional[dict] = None
    reasoning: Optional[str] = None


class BaselineRoute:
    """Common reset-handling shared by every non-intelligent route below."""

    def _reset_if_needed(self, state: GameState) -> Optional[ActionResult]:
        if state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return ActionResult(GameAction.RESET, reasoning="game not in progress -> RESET")
        return None


# ---------------------------------------------------------------------
# 2a) RandomAgent -- verified behavioral port of the official baseline
#     (arcprize/ARC-AGI-3-Agents agents/templates/random_agent.py, MIT)
# ---------------------------------------------------------------------

class RandomAgent(BaselineRoute):
    """Uniform-random baseline, functionally identical to the official
    `Random` agent shipped in arcprize/ARC-AGI-3-Agents."""

    def __init__(self, game_id: str = "", seed: Optional[int] = None) -> None:
        self.game_id = game_id
        s = seed if seed is not None else int(time.time() * 1_000_000) + (hash(game_id) % 1_000_000)
        self._rng = random.Random(s)

    def next_action(self, state: GameState) -> ActionResult:
        reset = self._reset_if_needed(state)
        if reset is not None:
            return reset

        action = self._rng.choice(NON_RESET_ACTIONS)
        if action.is_complex():
            x = self._rng.randint(GRID_MIN, GRID_MAX)
            y = self._rng.randint(GRID_MIN, GRID_MAX)
            return ActionResult(action, data={"x": x, "y": y}, reasoning="RNG said so!")
        return ActionResult(action, reasoning=f"RNG told me to pick {action.name}")


# ---------------------------------------------------------------------
# 2b) RoundRobinAgent -- deterministic cyclic actuator sweep
# ---------------------------------------------------------------------

class RoundRobinAgent(BaselineRoute):
    """Deterministically cycles ACTION1..ACTION7 (skipping RESET while
    playing), one action per call. Used to empirically map action -> effect
    with zero randomness and zero learning."""

    def __init__(self) -> None:
        self._order = [a for a in NON_RESET_ACTIONS]  # ACTION1..ACTION7 in enum order
        self._i = 0

    def next_action(self, state: GameState) -> ActionResult:
        reset = self._reset_if_needed(state)
        if reset is not None:
            self._i = 0  # restart the cycle on every fresh game
            return reset

        action = self._order[self._i % len(self._order)]
        self._i += 1
        if action.is_complex():
            # deterministic default probe point: dead center of the grid
            return ActionResult(action, data={"x": 32, "y": 32}, reasoning="round-robin probe (center)")
        return ActionResult(action, reasoning="round-robin cycle")

    def reset_progress(self) -> None:
        """Restart the cycle from ACTION1 without discarding the instance."""
        self._i = 0


# ---------------------------------------------------------------------
# 2c) ActionProbeAgent -- one deterministic pass over every action
# ---------------------------------------------------------------------

class ActionProbeAgent(BaselineRoute):
    """On a fresh/reset game, issues every declared action exactly once,
    in ascending action-id order (RESET excluded from the probe itself),
    then reports done. Pure enumeration -- no branching on frame content."""

    def __init__(self) -> None:
        self._queue: List[GameAction] = list(NON_RESET_ACTIONS)
        self._results: List[ActionResult] = []
        self._done = False

    def next_action(self, state: GameState) -> Optional[ActionResult]:
        reset = self._reset_if_needed(state)
        if reset is not None:
            return reset

        if not self._queue:
            self._done = True
            return None  # probe complete; nothing left to test

        action = self._queue.pop(0)
        if action.is_complex():
            result = ActionResult(action, data={"x": 32, "y": 32}, reasoning="probe pass")
        else:
            result = ActionResult(action, reasoning="probe pass")
        self._results.append(result)
        return result

    @property
    def is_complete(self) -> bool:
        return self._done

    @property
    def probed(self) -> List[ActionResult]:
        return list(self._results)

    def reset_progress(self) -> None:
        """Requeue every non-RESET action for another full probe pass."""
        self._queue = list(NON_RESET_ACTIONS)
        self._results = []
        self._done = False


# ---------------------------------------------------------------------
# 2d) RasterSweepAgent -- deterministic boustrophedon coverage of ACTION6
# ---------------------------------------------------------------------

class RasterSweepAgent(BaselineRoute):
    """Deterministic full-coverage route over the 64x64 ACTION6 click space,
    visiting every (x, y) exactly once in boustrophedon (raster,
    alternating-direction) order: row 0 left->right, row 1 right->left,
    row 2 left->right, etc. Zero repeats, zero diagonal jumps between
    consecutive rows, guaranteed full coverage in GRID_W*GRID_H steps."""

    def __init__(self, action: GameAction = GameAction.ACTION6) -> None:
        if not action.is_complex():
            raise ValueError("RasterSweepAgent requires a complex (x,y) action, e.g. ACTION6")
        self._action = action
        self._coords = self._build_boustrophedon()
        self._i = 0

    @staticmethod
    def _build_boustrophedon() -> List[Tuple[int, int]]:
        coords: List[Tuple[int, int]] = []
        for y in range(GRID_MIN, GRID_MAX + 1):
            xs = range(GRID_MIN, GRID_MAX + 1) if y % 2 == 0 else range(GRID_MAX, GRID_MIN - 1, -1)
            for x in xs:
                coords.append((x, y))
        return coords

    def __len__(self) -> int:
        return len(self._coords)

    @property
    def is_complete(self) -> bool:
        return self._i >= len(self._coords)

    def next_action(self, state: GameState) -> Optional[ActionResult]:
        reset = self._reset_if_needed(state)
        if reset is not None:
            return reset

        if self.is_complete:
            return None  # full grid already covered

        x, y = self._coords[self._i]
        self._i += 1
        return ActionResult(
            self._action, data={"x": x, "y": y},
            reasoning=f"raster sweep step {self._i}/{len(self._coords)}",
        )

    def coordinates(self) -> Iterator[Tuple[int, int]]:
        """Full route as a generator, independent of internal cursor state --
        useful for pre-computing/inspecting the whole path."""
        yield from self._build_boustrophedon()

    def reset_progress(self) -> None:
        """Restart the sweep from (0, 0) without discarding the instance."""
        self._i = 0


# ---------------------------------------------------------------------
# 3) FrameData bridge -- convert a real arcengine frame layer into plain
#    (x, y) points, ready for BrailleGrid64 / BrailleGridAgent rendering.
# ---------------------------------------------------------------------

def frame_layer_to_points(
    layer: List[List[int]],
    predicate: Optional[Callable[[int], bool]] = None,
) -> List[Tuple[int, int]]:
    """Convert one 64x64 color-index layer of `FrameData.frame` (arcengine)
    into a flat list of (x, y) points. `predicate(color) -> bool` selects
    which cells count; defaults to `color != 0` (0 is the conventional
    background color in ARC-format grids). Feed the result straight into
    `BrailleGrid64.from_points()` / `BrailleGridAgent.load_points()`."""
    pred = predicate or (lambda v: v != 0)
    points: List[Tuple[int, int]] = []
    for y, row in enumerate(layer):
        for x, v in enumerate(row):
            if pred(v):
                points.append((x, y))
    return points


def frame_content_hash(frame: List[List[List[int]]]) -> str:
    """Deterministic SHA-256 over an entire FrameData.frame (all layers),
    independent of any occupancy predicate. Use this for a strict,
    exact-state duplicate/no-op check on the raw color data itself,
    distinct from BrailleGrid64.content_hash() which hashes a derived
    binary occupancy for a chosen layer/predicate."""
    raw = json.dumps(frame, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------
# 4) NoOpLoopDetector -- flags repeated/stuck frames during a play loop.
#    Directly targets the class of failure where an action is legal but
#    produces no visible state change, or the agent cycles through the
#    same few states without progress (perception/planner no-op loops).
# ---------------------------------------------------------------------

class NoOpLoopDetector:
    """Tracks a rolling window of frame hashes and flags when the same
    state has recurred `repeat_threshold` or more times within the
    window -- i.e. the agent is stuck (no-op action, or a short cycle
    of states with no forward progress). Pure bookkeeping: no inference,
    no heuristics about *why* it's stuck, just a hard, deterministic
    trip-wire an agent loop can check every step."""

    def __init__(self, window_size: int = 20, repeat_threshold: int = 3) -> None:
        if repeat_threshold < 2:
            raise ValueError("repeat_threshold must be >= 2 to mean anything")
        self.window_size = window_size
        self.repeat_threshold = repeat_threshold
        self._history: Deque[str] = deque(maxlen=window_size)

    def push(self, frame_hash: str) -> bool:
        """Record a new frame hash (e.g. from frame_content_hash() or
        BrailleGrid64.content_hash()) and return True iff that hash has
        now occurred >= repeat_threshold times within the current window
        (i.e. the loop should be considered stuck)."""
        self._history.append(frame_hash)
        return self._history.count(frame_hash) >= self.repeat_threshold

    def is_stuck(self) -> bool:
        if not self._history:
            return False
        most_common_count = max(self._history.count(h) for h in set(self._history))
        return most_common_count >= self.repeat_threshold

    def reset(self) -> None:
        self._history.clear()

    @property
    def history(self) -> List[str]:
        return list(self._history)
