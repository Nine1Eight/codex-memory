from __future__ import annotations
from dataclasses import dataclass

from adapters.base import RuntimeAdapter
from adl import DifferenceEngine, ReflectionEngine
from detectors import PerceptionEngine
from ghostbridge import GhostBridge
from memory.store import MemoryStore
from planning.loops import LoopGuard, ResetPolicy
from planning.planner import ActionValidator, ScoreAwarePlanner
from planning.reversepath import ReversePath
from prl.router import AdaptivePerceptionRouter
from prl.sid import SemanticIDDecoder
from scheduler.games import GameScheduler
from telemetry.events import Telemetry
from world.causal import CausalTransitionGraph
from world.twin import EnvironmentTwin


@dataclass(slots=True)
class RunResult:
    game_id: str; steps: int; level: int; progress: float; completed: bool; failed: bool


class ARCController:
    def __init__(self, runtime: RuntimeAdapter, memory_path="checkpoints/memory.json", telemetry_path="logs/agent.jsonl") -> None:
        self.runtime = runtime; self.sid = SemanticIDDecoder(); self.router = AdaptivePerceptionRouter(); self.perception = PerceptionEngine()
        self.diff = DifferenceEngine(); self.reflector = ReflectionEngine(); self.graph = CausalTransitionGraph(); self.twin = EnvironmentTwin()
        self.ghostbridge = GhostBridge(); self.reversepath = ReversePath(); self.validator = ActionValidator(); self.memory = MemoryStore(memory_path); self.telemetry = Telemetry(telemetry_path)

    def run(self, max_steps_per_game: int = 1000) -> list[RunResult]:
        scheduler = GameScheduler(self.runtime.game_ids()); results = []
        while scheduler.has_games(): results.append(self.run_game(scheduler.select_next_game(), max_steps_per_game))
        return results

    def run_game(self, game_id: str, max_steps: int) -> RunResult:
        session = self.runtime.open_game_once(game_id); first = session.first_observation(); prior = self.sid.infer(game_id)
        detectors = self.router.select(prior, requested=self.ghostbridge.requested_detectors); world = self.perception.process(first, detectors)
        planner = ScoreAwarePlanner(self.twin, self.graph); loops = LoopGuard(); reset = ResetPolicy(); steps = 0
        self.telemetry.emit("game_started", game_id=game_id, state=world.state_key)
        try:
            while not world.game_complete and steps < max_steps:
                known = planner.shortest_reliable_plan(world)
                if known and known.confidence >= 0.7: plan = known
                else:
                    reverse = self.reversepath.analyze(world, self.graph); gap = reverse.gap or self.ghostbridge.find_gap(world, self.graph)
                    if gap:
                        plan = planner.minimum_discriminating_experiment(self.ghostbridge.best_hypothesis(gap, world), world)
                    else: plan = planner.best_progress_plan(world)
                action = self.validator.validate(plan.next_action(), world); prediction = self.twin.predict(world, action)
                self.telemetry.emit("pre_move", game_id=game_id, step=steps, state=world.state_key, action=action.action_id, prediction=prediction.confidence, plan=plan.source)
                actual = session.execute(action); detectors = self.router.select(prior, requested=self.ghostbridge.requested_detectors)
                new_world = self.perception.process(actual, detectors, world); delta = self.diff.diff(world, new_world); reflection = self.reflector.reflect(prediction, new_world, delta)
                self.graph.update(world, action, new_world, reflection); self.twin.update(world, reflection); self.router.update(reflection); self.ghostbridge.update(reflection); self.memory.update(reflection)
                looped, reason = loops.observe(new_world, action, reflection); self.telemetry.emit("post_move", game_id=game_id, step=steps, outcome=reflection.outcome.value, delta=delta.summary(), prediction_error=reflection.prediction_error, loop=reason)
                world = new_world; steps += 1
                if world.level_complete: self.memory.commit_level(world)
                if reset.should_reset(world, looped):
                    world = self.perception.process(session.reset_level(), detectors, world); self.telemetry.emit("level_reset", game_id=game_id, step=steps, reason=reason or "unrecoverable")
            self.memory.commit_game(world); return RunResult(game_id, steps, world.level, world.progress, world.game_complete, world.failed)
        finally: session.close()
