from __future__ import annotations


OWNERSHIP = {
    "ADL": {"owns": frozenset({"observations","evidence","hypotheses","uncertainty","rules","conclusions","experiment_proposals"}), "forbidden": frozenset({"action_commit","world_state_mutation"})},
    "GhostBridge": {"owns": frozenset({"causal_transition_graph","environment_twin","reachability","reverse_path","minimum_bridge","plan_simulation"}), "forbidden": frozenset({"evidence_truth","hypothesis_confidence","rule_promotion"})},
    "RHAE": {"owns": frozenset({"arbitration","single_legal_action_commit"}), "forbidden": frozenset({"observation_reinterpretation","evidence_mutation"})},
    "RDL": {"owns": frozenset({"runtime_delta_validation","action_observation_alignment"}), "forbidden": frozenset({"semantic_conclusions"})},
}


def assert_owner(component: str, capability: str) -> None:
    if capability not in OWNERSHIP[component]["owns"]: raise PermissionError(f"{component} does not own {capability}")
