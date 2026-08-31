"""Command line interface for the offline framework."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from src.causality.analysis import CausalAnalyzer
from src.models.canonical import canonical_json, primitive, stable_hash
from src.models.scenario import ScenarioError, load_scenario
from src.oracles.failure import FailureOracle
from src.replay.manager import ReplayManager
from src.reporting.report import Reporter
from src.search.engine import STRATEGIES, SearchEngine
from src.simulator.engine import Simulator
from src.submission.adapter import SubmissionAdapter, SubmissionError

LOG = logging.getLogger("agentsec")


def _actions(path: Path) -> list[Any]:
    return Simulator.actions_from_json(path.read_text(encoding="utf-8"))


def _write(path: Path | None, value: str) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    else:
        print(value, end="" if value.endswith("\n") else "\n")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="agentsec")
    root.add_argument(
        "--log-level", default="WARNING", choices=("DEBUG", "INFO", "WARNING", "ERROR")
    )
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("validate-scenario",):
        item = commands.add_parser(name)
        item.add_argument("scenario", type=Path)
    run = commands.add_parser("run-scenario")
    run.add_argument("scenario", type=Path)
    run.add_argument("actions", type=Path)
    explore = commands.add_parser("explore")
    explore.add_argument("scenario", type=Path)
    explore.add_argument("--strategy", choices=sorted(STRATEGIES), default="bfs")
    explore.add_argument("--output", type=Path)
    replay = commands.add_parser("replay")
    replay.add_argument("scenario", type=Path)
    replay.add_argument("actions", type=Path)
    replay.add_argument("--runs", type=int, default=3)
    minimize = commands.add_parser("minimize")
    minimize.add_argument("scenario", type=Path)
    minimize.add_argument("actions", type=Path)
    minimize.add_argument("--output", type=Path)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("scenario", type=Path)
    evaluate.add_argument("actions", type=Path)
    submit = commands.add_parser("build-submission")
    submit.add_argument("official_schema", type=Path)
    submit.add_argument("artifact", type=Path)
    submit.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("generate-report")
    report.add_argument("scenario", type=Path)
    report.add_argument("--strategy", choices=sorted(STRATEGIES), default="bfs")
    report.add_argument("--output", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='{"level":"%(levelname)s","message":"%(message)s"}',
    )
    try:
        if args.command == "validate-scenario":
            scenario = load_scenario(args.scenario)
            print(canonical_json({"valid": True, "scenario_hash": stable_hash(scenario)}))
            return 0
        if args.command == "build-submission":
            adapter = SubmissionAdapter(args.official_schema)
            artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
            payload, manifest = adapter.build(artifact, bool(artifact.get("replayable")))
            _write(args.output, payload + "\n")
            _write(args.output.with_suffix(".manifest.json"), canonical_json(manifest) + "\n")
            return 0
        scenario = load_scenario(args.scenario)
        if args.command == "run-scenario":
            state = Simulator(scenario).run(_actions(args.actions))
            print(canonical_json({"state_hash": state.state_hash, "events": state.history}))
            return 0
        if args.command == "replay":
            actions = _actions(args.actions)
            manager = ReplayManager()
            result = manager.verify(scenario, manager.package(scenario, actions), args.runs)
            print(canonical_json(result))
            return 0 if result.reliable else 2
        if args.command == "minimize":
            artifact = ReplayManager().minimize_to_artifact(scenario, _actions(args.actions))
            _write(args.output, canonical_json(artifact.export()) + "\n")
            return 0
        if args.command == "evaluate":
            actions = _actions(args.actions)
            state = Simulator(scenario).run(actions)
            findings = FailureOracle().evaluate(scenario, state)
            causal = CausalAnalyzer().analyze(scenario, actions)
            print(canonical_json({"findings": findings, "causality": causal}))
            return 0
        engine = SearchEngine(scenario, args.strategy)
        results = engine.explore()
        if args.command == "explore":
            _write(args.output, canonical_json(results) + "\n")
            return 0
        causal_graphs = [
            primitive(CausalAnalyzer().analyze(scenario, list(result.actions)))
            for result in results
        ]
        report = Reporter().build(results, engine.archive, causal_graphs)
        _write(args.output, Reporter().json(report))
        return 0
    except (ScenarioError, SubmissionError, ValueError, OSError, json.JSONDecodeError) as exc:
        LOG.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
