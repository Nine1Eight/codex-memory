from nsl.arc_loop import ARCMoveTrace, ARCPerMoveController
from nsl.models import Capability, CapabilityGraph, Evidence, EvidenceKind, FailureTrace, SystemSnapshot
from nsl.runtime import CandidateAction


def _snapshot_with_missing_memory() -> tuple[CapabilityGraph, SystemSnapshot]:
    graph = CapabilityGraph()
    graph.add(Capability(id="state", name="State Signature", description="", required_for=("arc",)))
    graph.add(Capability(id="memory", name="Move Memory", description="", required_for=("arc",), depends_on=("state",)))
    snapshot = SystemSnapshot(
        name="arc-agent",
        objective="arc",
        evidence=(Evidence("memory", EvidenceKind.REMOVED, 0.92, "version-diff"),),
        failures=(
            FailureTrace(
                id="f-memory",
                objective="arc",
                symptom="move-level delta missing",
                expected="write delta before next decision",
                observed="no move trace exists",
                severity=0.95,
                implicated_capabilities=("memory",),
            ),
        ),
    )
    return graph, snapshot


def test_arc_controller_preflight_blocks_before_env_step() -> None:
    graph, snapshot = _snapshot_with_missing_memory()
    trace = ARCMoveTrace(
        move_index=1,
        environment_signature="state-1",
        snapshot=snapshot,
        proposed_actions=(CandidateAction("rollout", "needs memory", ("memory",), 0.99),),
    )

    decision, negative_space_map = ARCPerMoveController(graph).preflight(trace)

    assert decision.status == "blocked"
    assert decision.selected is None
    assert "memory" in negative_space_map.gaps


def test_arc_controller_preflight_selects_safe_action() -> None:
    graph, snapshot = _snapshot_with_missing_memory()
    trace = ARCMoveTrace(
        move_index=1,
        environment_signature="state-1",
        snapshot=snapshot,
        proposed_actions=(
            CandidateAction("rollout", "needs memory", ("memory",), 0.99),
            CandidateAction("safe_probe", "uses visible state", ("state",), 0.4),
        ),
    )

    decision, _ = ARCPerMoveController(graph).preflight(trace)

    assert decision.status == "selected"
    assert decision.selected is not None
    assert decision.selected.name == "safe_probe"


def test_arc_controller_reports_bridge_candidates_when_enabled() -> None:
    graph, snapshot = _snapshot_with_missing_memory()
    trace = ARCMoveTrace(
        move_index=1,
        environment_signature="state-1",
        snapshot=snapshot,
        proposed_actions=(CandidateAction("rollout", "needs memory", ("memory",), 0.99),),
    )

    decision, _ = ARCPerMoveController(graph, instantiate_bridges=True).preflight(trace)

    assert decision.status == "bridge_required"
    assert ARCPerMoveController.bridge_ids(decision) == ("memory",)
