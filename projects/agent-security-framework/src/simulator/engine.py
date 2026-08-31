"""Purely local deterministic state-transition engine."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from src.mock_tools.registry import MockToolRegistry, ToolResult
from src.models.scenario import Artifact, Scenario
from src.models.state import Event, SimulatorState
from src.simulator.defense import SemanticDefense


class TransitionError(ValueError):
    pass


class SimulatorLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Action:
    tool: str
    parameters: dict[str, Any]
    provenance: tuple[str, ...] = ()


def _artifact_maps(artifacts: tuple[Artifact, ...]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {
        kind: {} for kind in ("file", "web", "api", "database", "memory")
    }
    for artifact in artifacts:
        if artifact.kind in groups:
            groups[artifact.kind][artifact.artifact_id] = artifact.content
    return groups


class Simulator:
    def __init__(
        self,
        scenario: Scenario,
        registry: MockToolRegistry | None = None,
        defense: SemanticDefense | None = None,
    ) -> None:
        self.scenario = scenario
        self.registry = registry or MockToolRegistry.default()
        self.defense = defense
        self.started_ns = time.monotonic_ns()

    def initial_state(self) -> SimulatorState:
        groups = _artifact_maps(self.scenario.initial_world)
        provenance: dict[str, tuple[str, ...]] = {
            a.artifact_id: (a.provenance,) for a in self.scenario.initial_world
        }
        messages = tuple(
            {
                "id": a.artifact_id,
                "content": a.content,
                "trust": a.trust,
                "provenance": a.provenance,
            }
            for a in self.scenario.initial_world
            if a.kind == "message"
        )
        return SimulatorState(
            virtual_files={str(k): str(v) for k, v in groups["file"].items()},
            messages=messages,
            web_pages={str(k): str(v) for k, v in groups["web"].items()},
            api_records=groups["api"],
            database=groups["database"],
            memory=groups["memory"],
            permissions=frozenset(
                self.scenario.metadata.get("initial_permissions", self.scenario.permissions)
            ),
            provenance=provenance,
        )

    def _check_limits(self, state: SimulatorState) -> None:
        budgets = self.scenario.budgets
        if state.steps >= budgets.max_steps or len(state.history) >= budgets.max_events:
            raise SimulatorLimitError("step or event budget exhausted")
        from src.models.canonical import canonical_json

        state_bytes = len(canonical_json(state).encode("utf-8"))
        if state_bytes > budgets.max_virtual_bytes:
            raise SimulatorLimitError("simulated state memory budget exceeded")
        elapsed_ms = (time.monotonic_ns() - self.started_ns) // 1_000_000
        if elapsed_ms > budgets.timeout_ms:
            raise SimulatorLimitError("simulator wall-clock budget exceeded")

    def transition(
        self, state: SimulatorState, action: Action, observation: dict[str, Any] | None = None
    ) -> SimulatorState:
        """Return next_state = transition(state, simulated_action, simulated_observation)."""
        self._check_limits(state)
        if state.terminal is not None:
            raise TransitionError("cannot transition a terminal state")
        specs = {tool.name: tool for tool in self.scenario.tools}
        if action.tool not in specs or action.tool not in self.scenario.allowed_actions:
            raise TransitionError(f"tool is unavailable or not allowed: {action.tool}")
        spec = specs[action.tool]
        if set(action.parameters) != set(spec.parameters):
            raise TransitionError(f"parameters for {action.tool} must be {sorted(spec.parameters)}")
        type_map: dict[str, type[Any] | tuple[type[Any], ...]] = {
            "string": str,
            "integer": int,
            "boolean": bool,
            "object": dict,
        }
        for name, declared_type in spec.parameters.items():
            value = action.parameters[name]
            if declared_type == "integer" and isinstance(value, bool):
                raise TransitionError(f"parameter {name} must be integer, not boolean")
            if not isinstance(value, type_map[declared_type]):
                raise TransitionError(f"parameter {name} must be {declared_type}")
        authorized = spec.permission in state.permissions
        if self.defense is not None:
            decision = self.defense.evaluate(state, action, spec)
            if not decision.allow:
                event = Event(
                    index=len(state.history),
                    event_type="defense_blocked",
                    tool=action.tool,
                    parameters=dict(action.parameters),
                    result={
                        "risk_score": decision.risk_score,
                        "activation_level": decision.activation_level,
                        "reasons": list(decision.reasons),
                        "observation": observation or {},
                    },
                    trust="untrusted" if action.provenance else "trusted",
                    provenance=action.provenance,
                    permission=spec.permission,
                    authorized=False,
                )
                next_state = state.with_event(event)
                self._check_limits_after_transition(next_state)
                return next_state
        result: ToolResult = self.registry.invoke(spec, state, action.parameters, authorized)
        trust = "untrusted" if action.provenance else "trusted"
        event = Event(
            index=len(state.history),
            event_type=result.event_type,
            tool=action.tool,
            parameters=dict(action.parameters),
            result={**result.data, "observation": observation or {}},
            trust=trust,
            provenance=action.provenance,
            permission=spec.permission,
            authorized=authorized,
        )
        changes = result.apply(state)
        next_state = state.with_event(event, **changes)
        self._check_limits_after_transition(next_state)
        return next_state

    def _check_limits_after_transition(self, state: SimulatorState) -> None:
        from src.models.canonical import canonical_json

        if len(canonical_json(state).encode("utf-8")) > self.scenario.budgets.max_virtual_bytes:
            raise SimulatorLimitError("simulated state memory budget exceeded")

    def run(self, actions: list[Action]) -> SimulatorState:
        state = self.initial_state()
        for action in actions:
            state = self.transition(state, action)
        return state

    @staticmethod
    def snapshot(state: SimulatorState) -> str:
        from src.models.canonical import canonical_json

        return canonical_json(state)

    @staticmethod
    def restore_snapshot(snapshot: str) -> SimulatorState:
        try:
            data = json.loads(snapshot)
            events = tuple(
                Event(
                    index=int(item["index"]),
                    event_type=str(item["event_type"]),
                    tool=str(item["tool"]),
                    parameters=dict(item["parameters"]),
                    result=dict(item["result"]),
                    trust=str(item["trust"]),
                    provenance=tuple(item["provenance"]),
                    permission=str(item["permission"]),
                    authorized=bool(item["authorized"]),
                )
                for item in data["history"]
            )
            return SimulatorState(
                virtual_files=dict(data["virtual_files"]),
                messages=tuple(data["messages"]),
                web_pages=dict(data["web_pages"]),
                api_records=dict(data["api_records"]),
                database=dict(data["database"]),
                memory=dict(data["memory"]),
                permissions=frozenset(data["permissions"]),
                history=events,
                provenance={key: tuple(value) for key, value in data["provenance"].items()},
                terminal=data["terminal"],
                steps=int(data["steps"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TransitionError(f"invalid simulator snapshot: {exc}") from exc

    def replay(
        self, actions: list[Action], expected_hashes: list[str] | None = None
    ) -> SimulatorState:
        state = self.initial_state()
        hashes = [state.state_hash]
        for action in actions:
            state = self.transition(state, action)
            hashes.append(state.state_hash)
        if expected_hashes is not None and hashes != expected_hashes:
            raise TransitionError("deterministic replay hash mismatch")
        return state

    @staticmethod
    def action_from_dict(data: dict[str, Any]) -> Action:
        if set(data) != {"tool", "parameters", "provenance"}:
            raise TransitionError("action fields must be tool, parameters, provenance")
        return Action(str(data["tool"]), dict(data["parameters"]), tuple(data["provenance"]))

    @staticmethod
    def actions_from_json(text: str) -> list[Action]:
        value = json.loads(text)
        if not isinstance(value, list):
            raise TransitionError("actions must be a JSON list")
        return [Simulator.action_from_dict(item) for item in value]
