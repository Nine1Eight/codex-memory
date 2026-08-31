# ADLDB / GhostBridge ARC-AGI-3 agent

This repository contains a connected ARC-AGI-3 control loop designed for Termux development and Kaggle competition execution. The deterministic system performs observation normalization, adaptive detector routing, entity tracking, topology mapping, ADL state differences, causal transition learning, executable twin prediction, GhostBridge gap/hypothesis generation, ReversePath analysis, score-aware planning, validation, execution, and reflection.

The production boundary is `RuntimeAdapter`. `BoundRuntimeAdapter` binds official or local ARC game objects without importing Kaggle-only packages on Android. It enforces one opened environment per game and sends reset through a separate control boundary. Missing official runtime components raise `RuntimeBoundaryError`; they are never replaced with synthetic success.

## Termux workflows

```sh
./scripts/bootstrap_termux.sh
./scripts/verify_environment.sh
./scripts/test_all.sh
python -m pytest -q
python -m scoring.rhae --self-test
python -m agent.runtime --dry-run
python scripts/build_notebook.py
python scripts/verify_notebook.py
```

The runtime uses only the standard library. `pytest` is a development extra; the full local suite also runs with `unittest`. Kaggle-only `pandas` and `pyarrow` are optional extras.

## Validation status

- `TERMUX_VALIDATED`: imports, RHAE score invariants, observation→state→delta, prediction→reflection→causal/twin learning, GhostBridge falsifiable tests, SID observation-authority updates, action validation, and notebook static contract.
- `KAGGLE_VALIDATION_REQUIRED`: official gateway connectivity, attached offline ARC wheels, Qwen/vLLM GPU runtime, full hidden-game trajectories, `submission.parquet` acceptance, and competition score.

The downloaded Kaggle reference [johnny5.ipynb](kaggle/reference_johnny5/johnny5.ipynb) is preserved verbatim. The generated competition notebook retains its official one-environment-per-game, pre-move GhostBridge, post-move ADL audit, and fail-closed input/model checks. Its historical metadata score is provenance, not a claim that this source tree was re-scored locally.

## Controller invariant

Every ordinary environment action follows:

`plan → predict → validate → pre_move telemetry → execute real action → observe → perceive → diff → reflect → update graph/twin/router/GhostBridge/memory`

Reset is never passed through the ordinary action validator. Loop detection can trigger a controlled reset only for an unrecoverable terminal state, a repeated controlled comparison, or a known higher-value replay.
