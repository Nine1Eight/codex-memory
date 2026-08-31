# NoPriorsAgent

`NoPriorsAgent` is an ARC-AGI-3 hybrid agent that learns game-specific behavior
only from frames and transitions observed during the current run.

## Policy

- Object-centric connected-component scene representation.
- Per-state and global action-effect models.
- UCB exploration with no-effect, death, repeat, and loop penalties.
- Salient click targeting based on small and rare-colored components.
- Dead-click suppression after repeated unchanged frames.
- Successful within-run action macros transferred to later levels.
- Optional chronological-frame vision-language policy served on localhost.
- Deterministic symbolic fallback if the model server fails.

The source contains no public-game identifiers, hand-authored game rules,
recorded solutions, or evaluation-time external network calls.

## Run symbolic-only

```sh
python main.py --agent=nopriorsagent --game=ls20
```

## Run with an offline local VLM

Start an OpenAI-compatible vision-language server separately, then configure:

```sh
export NO_PRIORS_VLM_URL=http://127.0.0.1:8000/v1
export NO_PRIORS_VLM_MODEL=vllm-model
python main.py --agent=nopriorsagent
```

Only loopback hosts (`127.0.0.1`, `localhost`, or `::1`) are accepted. A strong
vision-language model is required; public ARC-AGI-3 milestone solutions used a
31B-class Gemma vision model. Package its weights and serving wheels as Kaggle
inputs because competition evaluation has no internet access.

Useful controls:

- `NO_PRIORS_MAX_ACTIONS` (default `240`)
- `NO_PRIORS_VLM_TIMEOUT` (default `120` seconds)
- `NO_PRIORS_VLM_URL`
- `NO_PRIORS_VLM_MODEL`

## Verification status

- Python compilation: passed.
- Six isolated policy checks: passed.
- No-prior source audit for known public game IDs: passed.
- Symbolic-only smoke run on five public environments: zero levels completed in
  240 actions. This fallback is robust infrastructure, not a competitive policy.
- Local-VLM leaderboard score: not measured in this workspace because the
  required vision model/server is not installed.

Do not describe this agent as high-scoring until the packaged VLM configuration
has been evaluated through the official competition scorer.
