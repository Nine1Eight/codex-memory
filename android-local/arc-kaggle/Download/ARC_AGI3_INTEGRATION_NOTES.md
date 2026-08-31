# Multiverse Oracle v1.1.0 — ARC-AGI-3 Integration

## Purpose

This release wires the Multiverse Oracle, ADL adapter, and GhostBridge adapter into a target-free ARC-AGI-3 closed loop. It does **not** assume a known target grid. The agent learns online from real frame transitions, legal-action metadata, level progress, terminal state, and repeated causal evidence.

## Execution pipeline

1. `ARCFrameAdapter` converts the current ARC frame into a normalized observation and legal action set.
2. `ARCStateEncoder` computes deterministic raw, palette-invariant, and palette+dihedral-invariant state keys.
3. `ARCOnlineDifferenceLearner` measures the observed transition delta from the last real frame.
4. `ARCTransitionModel` updates local/global action-outcome posteriors and observed causal evidence.
5. `ARCClickCandidateGenerator` creates bounded ACTION6 `(x,y)` candidates only when ACTION6 is legal.
6. `ARCBranchGenerator` samples Bayesian causal worlds and performs full multi-hop rollouts across the configured horizon.
7. `MultiverseOracleEngine` scores the sampled futures while preserving provenance boundaries.
8. `CrossWorldPlanner` selects a robust legal first action.
9. `GhostBridgeOracleAdapter` rejects strongly contradicted phantom transitions and diagnoses missing/phantom bridges.
10. `ADLOracleAdapter` exports observed difference/anomaly evidence for online learning.
11. `ARCEnvironmentRunner` executes the selected `GameAction`; complex action payloads are attached with `set_data(...)` when the official runtime exposes it.
12. The next **real** environment observation closes the loop and corrects the posterior.

## Epistemic invariant

Simulated branch facts can affect expected utility but cannot enter the executable state as observations. The validation suite verifies zero simulated-feature leakage through the ARC closed loop.

## Deployment: Kaggle Starter

Use `integrations/kaggle_starter/my_agent.py` as `agent/my_agent.py` in the current ARC-AGI-3 Kaggle starter and make the `multiverse_oracle` package importable in the notebook/runtime. The class is named `MyAgent` and implements the starter's `is_done(...)` and `choose_action(...)` contract.

## Deployment: ARC-AGI-3-Agents repo

Use `integrations/agents_repo/oracle_multiverse_agent.py` as an agent module in the official agents repository, or import `multiverse_oracle.arcagi3_agent.OracleARCAGI3Agent` directly when the repository's `agents` package is installed.

## Direct local execution

With the official ARC toolkit installed and environment files available:

```bash
python examples/arcagi3_direct_runner.py \
  --game ls20 \
  --mode offline \
  --max-actions 400 \
  --branches 96 \
  --horizon 5 \
  --report arc_ls20_report.json
```

Use the mode and environment directory appropriate for your ARC installation.

## Revalidation

After installing the wheel:

```bash
multiverse-oracle-arc3-validate --output arcagi3_validation_report.json
```

The packaged validation exercises simple legal actions, RESET/GAME_OVER handling, ACTION6 coordinate payloads, progress feedback, WIN handling, multi-hop branch planning, and the epistemic isolation invariant.

## Environment limitation of this build run

The build container used for v1.1.0 did not have `arc_agi`, `arcengine`, the official `agents` package, or ARC environment files mounted. Therefore this build records **contract-level and closed-loop deterministic validation**, not a claimed score on official ARC games or the Kaggle leaderboard. The adapters were implemented against the current public ARC API/agent contracts and include direct runtime entry points for verification in an ARC-enabled environment.
