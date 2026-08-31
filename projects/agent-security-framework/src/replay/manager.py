"""Repeated deterministic replay and action delta debugging."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from src.causality.analysis import CausalAnalyzer, CausalAnalysis
from src.models.canonical import primitive
from src.models.canonical import stable_hash
from src.models.scenario import Scenario
from src.oracles.failure import FailureOracle, Finding
from src.simulator.engine import Action, Simulator


@dataclass(frozen=True)
class ReplayPackage:
    scenario_hash: str
    seed: int
    actions: tuple[Action, ...]
    state_hashes: tuple[str, ...]
    terminal_hash: str


@dataclass(frozen=True)
class ReplayResult:
    reliable: bool
    runs: int
    terminal_hash: str
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class MinimizedTrajectory:
    actions: tuple[Action, ...]
    replay: ReplayResult
    replay_package: ReplayPackage
    causality: CausalAnalysis
    explanation: str

    def export(self) -> dict[str, object]:
        return {
            "actions": primitive(self.actions),
            "replay": primitive(self.replay),
            "replay_package": primitive(self.replay_package),
            "causality": primitive(self.causality),
            "explanation": self.explanation,
        }


class ReplayManager:
    def __init__(self, oracle: FailureOracle | None = None) -> None:
        self.oracle = oracle or FailureOracle()

    def package(self, scenario: Scenario, actions: list[Action]) -> ReplayPackage:
        simulator = Simulator(scenario)
        state = simulator.initial_state()
        hashes = [state.state_hash]
        for action in actions:
            state = simulator.transition(state, action)
            hashes.append(state.state_hash)
        return ReplayPackage(
            stable_hash(scenario), scenario.seed, tuple(actions), tuple(hashes), state.state_hash
        )

    def verify(self, scenario: Scenario, package: ReplayPackage, runs: int = 3) -> ReplayResult:
        if runs < 2 or package.scenario_hash != stable_hash(scenario):
            return ReplayResult(False, runs, "", ())
        terminal_hashes = []
        finding_sets = []
        for _ in range(runs):
            simulator = Simulator(scenario)
            state = simulator.replay(list(package.actions), list(package.state_hashes))
            terminal_hashes.append(state.state_hash)
            finding_sets.append(tuple(self.oracle.evaluate(scenario, state)))
        reliable = (
            len(set(terminal_hashes)) == 1
            and terminal_hashes[0] == package.terminal_hash
            and all(finding_sets[0] == x for x in finding_sets)
        )
        findings = tuple(
            Finding(**{**f.__dict__, "reproducible": reliable}) for f in finding_sets[0]
        )
        return ReplayResult(reliable, runs, terminal_hashes[0], findings)

    def minimize(self, scenario: Scenario, actions: list[Action]) -> list[Action]:
        def fails(candidate: list[Action]) -> bool:
            try:
                if not self.oracle.evaluate(scenario, Simulator(scenario).run(candidate)):
                    return False
                return (
                    CausalAnalyzer(self.oracle).analyze(scenario, candidate).status == "confirmed"
                )
            except Exception:
                return False

        if not fails(actions):
            raise ValueError("trajectory has no reproducible failure")
        result = list(actions)
        granularity = 2
        while len(result) >= 2:
            chunk = max(1, len(result) // granularity)
            reduced = False
            for start in range(0, len(result), chunk):
                candidate = result[:start] + result[start + chunk :]
                if candidate and fails(candidate):
                    result, reduced = candidate, True
                    break
            if not reduced:
                if granularity >= len(result):
                    break
                granularity = min(len(result), granularity * 2)
        # For bounded benchmark paths, prove shortestness over ordered subsets.
        examined = 0
        for length in range(1, len(result)):
            for indices in combinations(range(len(actions)), length):
                examined += 1
                if examined > scenario.budgets.max_candidates:
                    return result
                candidate = [actions[index] for index in indices]
                if fails(candidate):
                    return candidate
        return result

    def minimize_to_artifact(
        self, scenario: Scenario, actions: list[Action], runs: int = 3
    ) -> MinimizedTrajectory:
        minimized = self.minimize(scenario, actions)
        package = self.package(scenario, minimized)
        replay = self.verify(scenario, package, runs=runs)
        causality = CausalAnalyzer(self.oracle).analyze(scenario, minimized)
        findings = (
            ", ".join(sorted({finding.rule_id for finding in replay.findings})) or "no finding"
        )
        explanation = (
            f"Shortest reliable trajectory found with {len(minimized)} actions; "
            f"replay={replay.reliable}; findings={findings}; causality={causality.status}."
        )
        return MinimizedTrajectory(tuple(minimized), replay, package, causality, explanation)
