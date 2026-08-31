# ADL v2 competition artifact

This directory is a new, self-contained artifact derived from the reported
77.390 notebook lineage. The parent notebook under `ai_agent_security_existing/`
is not modified.

The attack is confined to the official offline `AttackEnvProtocol`, uses only
reserved `.example` destinations, and retains live candidates only when the
exported trace contains a successful payload-bearing `http.post`. ADL compares
four prompt families, records family-level reward and latency, and spends the
remaining replay budget on the best measured reward rate while periodically
testing a challenger.

Build and check locally:

```sh
python adl_attack_upgrade/build_notebook.py
python -m unittest -v adl_attack_upgrade/test_attack.py
python -m py_compile adl_attack_upgrade/attack.py
```

The generated notebook never fabricates a score or submission. On Kaggle, the
official `JEDAttackInferenceServer` remains the sole producer of
`submission.csv`.
