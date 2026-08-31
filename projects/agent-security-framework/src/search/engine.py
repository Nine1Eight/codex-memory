"""Bounded deterministic exploration strategies over simulated actions."""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

from src.causality.analysis import CausalAnalyzer
from src.evaluation.scoring import Evaluator
from src.models.canonical import stable_hash
from src.models.scenario import Scenario
from src.models.state import SimulatorState
from src.oracles.failure import FailureOracle, Finding
from src.replay.manager import ReplayManager
from src.simulator.defense import SemanticDefense
from src.simulator.engine import Action, Simulator, SimulatorLimitError, TransitionError


STRATEGIES = {"bfs", "dfs", "beam", "mcts", "coverage", "bandit", "novelty", "evolutionary"}


@dataclass(frozen=True)
class SearchResult:
    strategy: str
    actions: tuple[Action, ...]
    state_hash: str
    score: float
    findings: tuple[Finding, ...]


@dataclass
class SearchArchive:
    states: set[str] = field(default_factory=set)
    transitions: set[tuple[str, str]] = field(default_factory=set)
    trust_crossings: set[tuple[str, str]] = field(default_factory=set)
    permission_transitions: set[str] = field(default_factory=set)
    terminal_outcomes: set[str] = field(default_factory=set)

    def observe(self, before: SimulatorState, after: SimulatorState) -> bool:
        fresh = after.state_hash not in self.states
        self.states.add(after.state_hash)
        event = after.history[-1]
        self.transitions.add((event.tool, event.event_type))
        self.trust_crossings.add((event.trust, event.permission))
        if event.event_type.startswith("permission_"):
            self.permission_transitions.add(event.event_type)
        if after.terminal:
            self.terminal_outcomes.add(after.terminal)
        return fresh


@dataclass(frozen=True)
class _Outcome:
    state: SimulatorState
    path: tuple[Action, ...]
    fresh: bool
    score: float
    findings: tuple[Finding, ...]
    reward: float


class SearchEngine:
    def __init__(
        self, scenario: Scenario, strategy: str = "bfs", beam_width: int = 8, defend: bool = False
    ) -> None:
        if strategy not in STRATEGIES:
            raise ValueError(f"strategy must be one of {sorted(STRATEGIES)}")
        self.scenario = scenario
        self.strategy = strategy
        self.beam_width = beam_width
        self.oracle = FailureOracle()
        self.evaluator = Evaluator()
        self.replay_manager = ReplayManager(self.oracle)
        self.causal_analyzer = CausalAnalyzer(self.oracle)
        self.rng = random.Random(scenario.seed)
        self.defend = defend
        raw_actions = scenario.metadata.get("action_space", [])
        if not isinstance(raw_actions, list):
            raise ValueError("metadata.action_space must be a list")
        self.action_space = [Simulator.action_from_dict(item) for item in raw_actions]
        self.archive = SearchArchive()
        self._candidate_budget = 0
        self._results: list[SearchResult] = []
        self._seen_result_keys: set[str] = set()

    def explore(self) -> list[SearchResult]:
        self._candidate_budget = 0
        self._results = []
        self._seen_result_keys = set()
        simulator = self._simulator()
        initial = simulator.initial_state()
        self.archive.states = {initial.state_hash}
        self.archive.transitions.clear()
        self.archive.trust_crossings.clear()
        self.archive.permission_transitions.clear()
        self.archive.terminal_outcomes.clear()
        if self.strategy in {"bfs", "dfs", "beam", "coverage", "novelty"}:
            self._explore_frontier(simulator, initial)
        elif self.strategy == "mcts":
            self._explore_mcts(simulator, initial)
        elif self.strategy == "bandit":
            self._explore_bandit(simulator, initial)
        else:
            self._explore_evolutionary(simulator, initial)
        return sorted(
            self._results, key=lambda item: (-item.score, len(item.actions), item.state_hash)
        )

    def _simulator(self) -> Simulator:
        return Simulator(self.scenario, defense=SemanticDefense() if self.defend else None)

    def _can_expand(self) -> bool:
        return self._candidate_budget < self.scenario.budgets.max_candidates

    def _action_order(self, path: tuple[Action, ...]) -> list[Action]:
        if self.strategy in {"bandit", "evolutionary"}:
            decorated = [
                (
                    stable_hash(
                        [
                            self.scenario.seed,
                            self.strategy,
                            len(path),
                            index,
                            action.tool,
                            action.parameters,
                        ]
                    ),
                    action,
                )
                for index, action in enumerate(self.action_space)
            ]
            decorated.sort()
            return [action for _, action in decorated]
        return list(self.action_space)

    def _state_priority(self, state: SimulatorState, actions: tuple[Action, ...]) -> float:
        coverage = len({event.event_type for event in state.history})
        untrusted = sum(bool(event.provenance) for event in state.history)
        if self.strategy == "novelty":
            return coverage * 2.0 + untrusted - len(actions) * 0.1
        if self.strategy == "coverage":
            return coverage + len(self.archive.transitions) * 0.01 - len(actions) * 0.1
        if self.strategy == "beam":
            return coverage + len(state.permissions) * 0.1 - len(actions) * 0.1
        return -len(actions)

    def _reward(self, state: SimulatorState, findings: tuple[Finding, ...], fresh: bool) -> float:
        coverage = len({event.event_type for event in state.history})
        severity = max((finding.severity for finding in findings), default=0.0)
        causal = any(finding.causal_status == "confirmed" for finding in findings)
        reproducible = any(finding.reproducible for finding in findings)
        return (
            severity
            + coverage * 0.2
            + (1.0 if fresh else 0.0)
            + (2.0 if causal else 0.0)
            + (2.0 if reproducible else 0.0)
        )

    def _transition(
        self, simulator: Simulator, state: SimulatorState, path: tuple[Action, ...], action: Action
    ) -> _Outcome | None:
        if not self._can_expand() or len(path) >= self.scenario.budgets.max_steps:
            return None
        self._candidate_budget += 1
        try:
            next_state = simulator.transition(state, action)
        except (TransitionError, SimulatorLimitError):
            return None
        fresh = self.archive.observe(state, next_state)
        next_path = (*path, action)
        findings = self._confirmed_findings(next_state, next_path)
        score = (
            self.evaluator.score(self.scenario, next_state, findings, fresh) if findings else 0.0
        )
        reward = self._reward(next_state, findings, fresh)
        return _Outcome(next_state, next_path, fresh, score, findings, reward)

    def _confirmed_findings(
        self, state: SimulatorState, path: tuple[Action, ...]
    ) -> tuple[Finding, ...]:
        findings = tuple(self.oracle.evaluate(self.scenario, state))
        if not findings:
            return ()
        self.archive.terminal_outcomes.update(finding.rule_id for finding in findings)
        replay = self.replay_manager.verify(
            self.scenario,
            self.replay_manager.package(self.scenario, list(path)),
            runs=3,
        )
        causality = self.causal_analyzer.analyze(self.scenario, list(path))
        confirmed = tuple(
            Finding(
                **{
                    **finding.__dict__,
                    "reproducible": replay.reliable,
                    "causal_status": causality.status,
                }
            )
            for finding in findings
        )
        if replay.reliable and causality.status == "confirmed":
            result_key = stable_hash([self.strategy, path, state.state_hash, confirmed])
            if result_key not in self._seen_result_keys:
                self._seen_result_keys.add(result_key)
                score = self.evaluator.score(self.scenario, state, confirmed, True)
                self._results.append(
                    SearchResult(self.strategy, path, state.state_hash, score, confirmed)
                )
            return confirmed
        return ()

    def _explore_frontier(self, simulator: Simulator, initial: SimulatorState) -> None:
        frontier: deque[tuple[SimulatorState, tuple[Action, ...]]] = deque([(initial, ())])
        while frontier and self._can_expand():
            if self.strategy == "dfs":
                state, path = frontier.pop()
            elif self.strategy == "bfs":
                state, path = frontier.popleft()
            else:
                best_index = max(
                    range(len(frontier)),
                    key=lambda idx: self._state_priority(frontier[idx][0], frontier[idx][1]),
                )
                state, path = frontier[best_index]
                del frontier[best_index]
            if len(path) >= self.scenario.budgets.max_steps:
                continue
            expansions: list[tuple[float, SimulatorState, tuple[Action, ...]]] = []
            for action in self._action_order(path):
                outcome = self._transition(simulator, state, path, action)
                if outcome is None:
                    continue
                if outcome.fresh and len(outcome.path) < self.scenario.budgets.max_steps:
                    expansions.append(
                        (
                            self._state_priority(outcome.state, outcome.path),
                            outcome.state,
                            outcome.path,
                        )
                    )
            if self.strategy == "beam":
                expansions.sort(key=lambda item: item[0], reverse=True)
                expansions = expansions[: self.beam_width]
            for _, next_state, next_path in expansions:
                frontier.append((next_state, next_path))

    def _explore_mcts(self, simulator: Simulator, initial: SimulatorState) -> None:
        visits: dict[str, int] = {initial.state_hash: 0}
        edge_visits: dict[tuple[str, int], int] = {}
        edge_rewards: dict[tuple[str, int], float] = {}
        while self._can_expand():
            state = initial
            path: tuple[Action, ...] = ()
            rollout: list[tuple[str, int]] = []
            total_reward = 0.0
            while len(path) < self.scenario.budgets.max_steps and self._can_expand():
                ordered_actions = self._action_order(path)
                unexplored = [
                    (index, action)
                    for index, action in enumerate(ordered_actions)
                    if (state.state_hash, index) not in edge_visits
                ]
                if unexplored:
                    index, action = unexplored[0]
                else:
                    parent_visits = max(1, visits.get(state.state_hash, 1))

                    def uct(item: tuple[int, Action]) -> float:
                        idx, _ = item
                        key = (state.state_hash, idx)
                        mean = edge_rewards.get(key, 0.0) / max(1, edge_visits.get(key, 1))
                        bonus = math.sqrt(2.0 * math.log(parent_visits + 1) / edge_visits[key])
                        return mean + bonus

                    index, action = max(enumerate(ordered_actions), key=uct)
                outcome = self._transition(simulator, state, path, action)
                if outcome is None:
                    break
                key = (state.state_hash, index)
                rollout.append(key)
                total_reward += outcome.reward
                path = outcome.path
                state = outcome.state
                visits[state.state_hash] = visits.get(state.state_hash, 0) + 1
                if outcome.findings:
                    total_reward += outcome.score
                    break
            for key in rollout:
                edge_visits[key] = edge_visits.get(key, 0) + 1
                edge_rewards[key] = edge_rewards.get(key, 0.0) + total_reward

    def _explore_bandit(self, simulator: Simulator, initial: SimulatorState) -> None:
        pull_counts: dict[tuple[int, int], int] = {}
        reward_sums: dict[tuple[int, int], float] = {}
        episodes = 0
        while self._can_expand():
            episodes += 1
            state = initial
            path: tuple[Action, ...] = ()
            episode_reward = 0.0
            chosen_arms: list[tuple[int, int]] = []
            while len(path) < self.scenario.budgets.max_steps and self._can_expand():
                ordered_actions = self._action_order(path)
                depth = len(path)

                def bandit_score(index: int) -> float:
                    arm = (depth, index)
                    if pull_counts.get(arm, 0) == 0:
                        return float("inf")
                    mean = reward_sums[arm] / pull_counts[arm]
                    bonus = math.sqrt(2.0 * math.log(episodes + 1) / pull_counts[arm])
                    return mean + bonus

                index = max(range(len(ordered_actions)), key=bandit_score)
                action = ordered_actions[index]
                outcome = self._transition(simulator, state, path, action)
                if outcome is None:
                    break
                arm = (depth, index)
                chosen_arms.append(arm)
                episode_reward += outcome.reward
                path = outcome.path
                state = outcome.state
                if outcome.findings:
                    episode_reward += outcome.score
                    break
            for arm in chosen_arms:
                pull_counts[arm] = pull_counts.get(arm, 0) + 1
                reward_sums[arm] = reward_sums.get(arm, 0.0) + episode_reward

    def _explore_evolutionary(self, simulator: Simulator, initial: SimulatorState) -> None:
        population: list[tuple[Action, ...]] = [()]
        survivors = max(2, min(self.beam_width, len(self.action_space) or 1))
        while self._can_expand():
            scored: list[tuple[float, tuple[Action, ...], SimulatorState | None]] = []
            for path in population:
                state = initial
                valid = True
                score = 0.0
                for action in path:
                    outcome = self._transition(simulator, state, path[: len(state.history)], action)
                    if outcome is None:
                        valid = False
                        break
                    state = outcome.state
                    score += outcome.reward
                scored.append((score if valid else -1.0, path, state if valid else None))
                if not self._can_expand():
                    break
            scored.sort(key=lambda item: (item[0], -len(item[1])), reverse=True)
            elites = [path for _, path, _ in scored[:survivors]]
            if not elites:
                break
            next_population: list[tuple[Action, ...]] = list(elites)
            for rank, parent in enumerate(elites):
                if not self._can_expand():
                    break
                ordered_actions = self._action_order(parent)
                append_action = ordered_actions[rank % len(ordered_actions)]
                if len(parent) < self.scenario.budgets.max_steps:
                    next_population.append((*parent, append_action))
                if parent:
                    replace_index = rank % len(parent)
                    replace_action = ordered_actions[(rank + 1) % len(ordered_actions)]
                    mutated = list(parent)
                    mutated[replace_index] = replace_action
                    next_population.append(tuple(mutated))
                    next_population.append(parent[:-1])
            unique_population: list[tuple[Action, ...]] = []
            seen: set[str] = set()
            for path in next_population:
                key = stable_hash(path)
                if key not in seen and len(path) <= self.scenario.budgets.max_steps:
                    seen.add(key)
                    unique_population.append(path)
            population = unique_population[: max(survivors * 3, survivors)]
