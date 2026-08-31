# ARC3 Glyph Agent Tool — Real Runtime Only 🧩

This package contains a real ARC-AGI-3 starter agent only.

No simulated game loop.  
No fallback `arcengine`.  
No fallback `GameAction`.  
No local fake frame runner.

The agent file must run inside the actual ARC-AGI-3 starter/runtime:

```text
agent/my_agent.py
```

## What the agent does

```text
real latest_frame
  ↓
extract grid / image-like observation
  ↓
flood-fill connected objects
  ↓
convert semantic classes to 8-dot Braille pixels
  ↓
infer actor + target
  ↓
learn action effects online from real frame transitions
  ↓
return real GameAction
```

Semantic pixels:

```text
wall   → W → ⠺
player → P → ⠏
goal   → G → ⠛
door   → D → ⠙
key    → K → ⠅
enemy  → E → ⠑
button → B → ⠃
empty  → .
```

## Install into your real starter

Use the starter folder you already run ARC-AGI-3 from.

```bash
cd ~/Downloads/arc3_glyph_agent_tool_real_only
make install-into-starter STARTER=~/arc3_api_run/ARC-AGI-3-Agents
```

or:

```bash
make install-into-starter STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
```

## Verify against the real starter imports

```bash
make verify-real STARTER=~/arc3_api_run/ARC-AGI-3-Agents
```

This checks that the real starter exposes:

```text
arcengine
agents.agent
GameAction
FrameData
GameState
Agent
```

It does not simulate a game.

## Run the real local runner

```bash
cd ~/arc3_api_run/ARC-AGI-3-Agents
ARC3_LOG=1 ARC3_LOG_DIR=./logs make play-local
```

For a specific game, if your starter Makefile supports `GAME=`:

```bash
ARC3_LOG=1 ARC3_LOG_DIR=./logs make play-local GAME=ls20
```

## Analyze real run logs

```bash
python3 ~/Downloads/arc3_glyph_agent_tool_real_only/scripts/analyze_logs.py ~/arc3_api_run/ARC-AGI-3-Agents/logs
```

## Environment knobs

```bash
ARC3_MAX_ACTIONS=300
ARC3_SEED=918
ARC3_LOG=1
ARC3_LOG_DIR=./logs
ARC3_COLOR_TOLERANCE=24
ARC3_MAX_COLORS=32
```

## Files

```text
agent/my_agent.py                      Real ARC agent
scripts/install_into_starter.sh        Installs into real starter
scripts/verify_real_starter.py         Checks real starter imports/contracts
scripts/run_real_local.sh              Installs then runs starter make play-local
scripts/analyze_logs.py                Summarizes real JSONL logs
scripts/no_mock_audit.py               Verifies package contains no mock/fallback runtime
configs/classes.example.json           Semantic class vocabulary reference
Makefile                               Linux commands
```

## Python 3.12 importlib/dataclass runner patch

If `make play-local` fails with:

```text
AttributeError: 'NoneType' object has no attribute '__dict__'
```

patch the real local runner loader:

```bash
cd ~/Downloads/arc3_glyph_agent_tool_real_only_v2
make patch-loader STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
```

This inserts:

```python
sys.modules[spec.name] = module
```

before `spec.loader.exec_module(module)` in the real starter's `scripts/play_local.py`.

This is not a mock. It only registers the module correctly for Python 3.12 dataclasses.

## Required next step after flat 0-level runs

If the console shows repeated action cycles and 0 completed levels, enable real frame probing:

```bash
cd ~/Downloads/arc3_glyph_agent_tool_real_only_v3
make install-into-starter STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
make patch-loader STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

GAME=tr87 STEPS=40 make probe STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
make summarize-probe STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
```

The probe writes:

```text
logs/frame_probe_<game>_<timestamp>.jsonl
```

This records actual `FrameData` fields, detected grid shape, class counts, scene object count, actor, and target. Use that file to patch the extractor against the real frame contract.

## 10,000-unit visible reflection budget

v4 adds an explicit planning budget:

```bash
ARC3_REFLECT_ENABLED=1
ARC3_REFLECT_BUDGET=10000
ARC3_REFLECT_DEPTH=8
ARC3_REFLECT_BRANCH=6
ARC3_REFLECT_WIN_REWARD=10000
ARC3_REFLECT_REMAINING_REWARD=250
```

The score function rewards:

```text
winning proxy
+ distance-to-target improvement
+ bonus for unused reflection budget
- repeated/stagnant action penalties
```

Run one real game with probe and reflection logs:

```bash
cd ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents" \
ARC3_LOG=1 \
ARC3_FRAME_PROBE=1 \
ARC3_FRAME_PROBE_N=8 \
ARC3_REFLECT_ENABLED=1 \
ARC3_REFLECT_BUDGET=10000 \
ARC3_LOG_DIR=./logs \
.venv/bin/python scripts/play_local.py --game tr87 --max-steps 200
```

Analyze:

```bash
cd ~/Downloads/arc3_glyph_agent_tool_real_only_v4_reflect
make summarize-probe STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
make analyze-reflection STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
```

## v4.1 syntax hotfix

v4.1 fixes a frame-probe preview typo and extends `make audit` to compile-check Python files.

For an already-installed v4 agent:

```bash
cd ~/Downloads/arc3_glyph_agent_tool_real_only_v4_1_reflect_fix
make hotfix STARTER=~/arc3_api_run/ARC-AGI-3-Kaggle-Starter
```

## v5 real frame fix

The tr87 frame probe showed:

```text
FrameData.frame = list[list[list[int]]]
outer length = 1
middle length = 64
inner length = 64
```

That is `C x H x W`, specifically a single 64x64 channel. Earlier builds treated it as a 1x64 RGB-like image, producing a false `height=1 width=64 values={0:64}` grid.

v5 fixes:

```text
1x64x64 / CxHxW frame unwrapping
latest_frame.available_actions filtering
```

Run tr87:

```bash
cd ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents" \
ARC3_LOG=1 \
ARC3_FRAME_PROBE=1 \
ARC3_FRAME_PROBE_N=8 \
ARC3_REFLECT_ENABLED=1 \
ARC3_REFLECT_BUDGET=10000 \
ARC3_REFLECT_DEPTH=8 \
ARC3_REFLECT_BRANCH=4 \
ARC3_REFLECT_WIN_REWARD=10000 \
ARC3_REFLECT_REMAINING_REWARD=250 \
ARC3_LOG_DIR=./logs \
.venv/bin/python scripts/play_local.py --game tr87 --max-steps 200
```

## v6 verified action effects

The v5 tr87 run no longer flat-cycled every available action, but it overcommitted to `ACTION3`.
That means reflection was active but using generic fallback direction assumptions too early.

v6 fixes:

```text
Reflection waits until each available action has real frame-effect tests.
Generic ACTION# fallback vectors are disabled after real testing.
No-change actions are excluded from vector planning.
If no action changes the frame, the policy round-robins instead of spamming ACTION3.
```

Run tr87:

```bash
cd ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents" \
ARC3_LOG=1 \
ARC3_FRAME_PROBE=1 \
ARC3_FRAME_PROBE_N=8 \
ARC3_REFLECT_ENABLED=1 \
ARC3_REFLECT_BUDGET=10000 \
ARC3_REFLECT_DEPTH=8 \
ARC3_REFLECT_BRANCH=4 \
ARC3_REFLECT_WIN_REWARD=10000 \
ARC3_REFLECT_REMAINING_REWARD=250 \
ARC3_LOG_DIR=./logs \
.venv/bin/python scripts/play_local.py --game tr87 --max-steps 200
```

## v7 progress-budget planner

The v6 logs show frame extraction is good:

```text
height=64 width=64
objects=62/63
actor=player
target=goal
```

They also show reflection spent the full 10,000-unit budget and selected only `ACTION1` late in the run. v7 fixes reflection economics and adds real progress learning.

v7 changes:

```text
ARC3_REFLECT_STEP_BUDGET=240 default
total 10,000 budget is preserved across the game
real actor-to-target distance progress is tracked per action
verified_progress_plan outranks generic vector plans
positive/negative progress is logged per action
```

Run:

```bash
cd ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents" \
ARC3_LOG=1 \
ARC3_FRAME_PROBE=1 \
ARC3_FRAME_PROBE_N=8 \
ARC3_REFLECT_ENABLED=1 \
ARC3_REFLECT_BUDGET=10000 \
ARC3_REFLECT_STEP_BUDGET=240 \
ARC3_REFLECT_DEPTH=8 \
ARC3_REFLECT_BRANCH=4 \
ARC3_REFLECT_WIN_REWARD=10000 \
ARC3_REFLECT_REMAINING_REWARD=250 \
ARC3_LOG_DIR=./logs \
.venv/bin/python scripts/play_local.py --game tr87 --max-steps 200
```

## v8 BVS A* NavigationGraph

v8 implements the BVS architecture route layer:

```text
Pixel Grid → Flood-Fill Object Detector → Braille Token Encoder → NavigationGraph/A* → BrailleAgent decision
```

New mode:

```text
bvs_astar_route_plan
```

It uses the real 64x64 semantic-pixel grid, actor object, target object, traversability affordances, and learned real action vectors. It does not use mock movement or simulated frames.

Run:

```bash
cd ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents" \
ARC3_LOG=1 \
ARC3_FRAME_PROBE=1 \
ARC3_FRAME_PROBE_N=8 \
ARC3_BVS_ASTAR_ENABLED=1 \
ARC3_REFLECT_ENABLED=1 \
ARC3_REFLECT_BUDGET=10000 \
ARC3_REFLECT_STEP_BUDGET=240 \
ARC3_REFLECT_DEPTH=8 \
ARC3_REFLECT_BRANCH=4 \
ARC3_REFLECT_WIN_REWARD=10000 \
ARC3_REFLECT_REMAINING_REWARD=250 \
ARC3_LOG_DIR=./logs \
.venv/bin/python scripts/play_local.py --game tr87 --max-steps 200
```

## v9 motion-role inference

v8 proved the grid is visible, but the logs still showed no route decisions. The likely issue is that generic BVS IDs do not equal tr87 roles: `2=player` and `3=goal` are BVS defaults, not guaranteed ARC game semantics.

v9 adds:

```text
motion-role inference from real consecutive frames
dynamic actor override before action-vector learning
dynamic target selection when static target is huge terrain
bvs_astar_diagnostic in every fallback decision
frame_probe actor/target object IDs, class IDs, areas, and centroids
```

Run:

```bash
cd ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter

PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents" \
ARC3_LOG=1 \
ARC3_FRAME_PROBE=1 \
ARC3_FRAME_PROBE_N=12 \
ARC3_BVS_ASTAR_ENABLED=1 \
ARC3_REFLECT_ENABLED=1 \
ARC3_REFLECT_BUDGET=10000 \
ARC3_REFLECT_STEP_BUDGET=240 \
ARC3_REFLECT_DEPTH=8 \
ARC3_REFLECT_BRANCH=4 \
ARC3_REFLECT_WIN_REWARD=10000 \
ARC3_REFLECT_REMAINING_REWARD=250 \
ARC3_LOG_DIR=./logs \
.venv/bin/python scripts/play_local.py --game tr87 --max-steps 200
```

Inspect route diagnostics:

```bash
grep -R '"bvs_astar_diagnostic"' ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter/logs/*.jsonl | tail -20
grep -R '"mode": "bvs_astar_route_plan"' ~/arc3_api_run/ARC-AGI-3-Kaggle-Starter/logs/*.jsonl | tail -20
```
