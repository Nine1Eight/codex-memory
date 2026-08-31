"""In-process mock tools with no host process or network capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from src.models.scenario import ToolSpec
from src.models.state import SimulatorState


@dataclass(frozen=True)
class ToolResult:
    event_type: str
    data: dict[str, Any]
    updates: dict[str, Any]

    def apply(self, state: SimulatorState) -> dict[str, Any]:
        return self.updates


Handler = Callable[[ToolSpec, SimulatorState, dict[str, Any], bool], ToolResult]


def _denied(spec: ToolSpec) -> ToolResult:
    return ToolResult(
        "permission_denied", {"reason": "simulated permission denied", "tool": spec.name}, {}
    )


def _file(spec: ToolSpec, state: SimulatorState, p: dict[str, Any], allowed: bool) -> ToolResult:
    if not allowed:
        return _denied(spec)
    files = dict(state.virtual_files)
    operation, path = str(p.get("operation", "")), str(p.get("path", ""))
    if operation == "read":
        return ToolResult("virtual_file_read", {"path": path, "content": files.get(path)}, {})
    if operation == "write":
        files[path] = str(p.get("content", ""))
        return ToolResult(
            "virtual_file_write",
            {"path": path, "bytes": len(files[path].encode())},
            {"virtual_files": files},
        )
    return ToolResult("mock_tool_error", {"reason": "unsupported virtual file operation"}, {})


def _record(kind: str, collection: str) -> Handler:
    def handler(
        spec: ToolSpec, state: SimulatorState, p: dict[str, Any], allowed: bool
    ) -> ToolResult:
        if not allowed:
            return _denied(spec)
        payload = {"synthetic": True, **p}
        if collection == "messages":
            return ToolResult(kind, payload, {"messages": (*state.messages, payload)})
        target = dict(getattr(state, collection))
        key = str(p.get("key", p.get("url", p.get("recipient", len(target)))))
        target[key] = payload
        return ToolResult(kind, payload, {collection: target})

    return handler


def _permission(
    spec: ToolSpec, state: SimulatorState, p: dict[str, Any], allowed: bool
) -> ToolResult:
    requested = str(p.get("permission", ""))
    operation = str(p.get("operation", "request"))
    if not allowed:
        return _denied(spec)
    permissions = set(state.permissions)
    if operation == "grant":
        permissions.add(requested)
        event = "permission_granted"
    elif operation == "revoke":
        permissions.discard(requested)
        event = "permission_revoked"
    else:
        event = "permission_requested"
    return ToolResult(event, {"permission": requested}, {"permissions": frozenset(permissions)})


class MockToolRegistry:
    def __init__(self, handlers: dict[str, Handler]) -> None:
        self.handlers = handlers

    @classmethod
    def default(cls) -> "MockToolRegistry":
        return cls(
            {
                "virtual_file": _file,
                "email": _record("simulated_email", "messages"),
                "browser": _record("simulated_browser", "web_pages"),
                "api": _record("simulated_api", "api_records"),
                "database": _record("simulated_database", "database"),
                "messaging": _record("simulated_message", "messages"),
                "memory": _record("simulated_memory", "memory"),
                "permission": _permission,
            }
        )

    def invoke(
        self, spec: ToolSpec, state: SimulatorState, parameters: dict[str, Any], authorized: bool
    ) -> ToolResult:
        handler = self.handlers.get(spec.kind)
        if handler is None:
            return ToolResult("mock_tool_error", {"reason": "no local handler"}, {})
        return handler(spec, state, parameters, authorized)
