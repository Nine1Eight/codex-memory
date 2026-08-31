#!/usr/bin/env bash
set -Eeuo pipefail
REPO="${ARC3_REPO:-$HOME/arc3_api_run/ARC-AGI-3-Agents}"
AGENT_SRC="${1:-$HOME/Downloads/generated_my_agent_v27_aggressive.py}"
PRIOR_SRC="${2:-$HOME/Downloads/sigil_arc3_prior_plans_ls20_7level_v27.json}"
if [ ! -d "$REPO" ]; then echo "[ERR] repo not found: $REPO"; exit 1; fi
if [ ! -f "$AGENT_SRC" ]; then echo "[ERR] agent not found: $AGENT_SRC"; exit 1; fi
if [ ! -f "$PRIOR_SRC" ]; then echo "[ERR] prior not found: $PRIOR_SRC"; exit 1; fi
cd "$REPO"
source .venv/bin/activate 2>/dev/null || true
mkdir -p "$HOME/arc3_logs"
cp "$AGENT_SRC" agents/my_agent.py
cp "$PRIOR_SRC" "$HOME/arc3_logs/sigil_arc3_prior_plans.json"
python -m py_compile agents/my_agent.py
unset SIGIL_DISABLE_BFS
export SIGIL_LOG_DIR="$HOME/arc3_logs"
export SIGIL_OBSERVER_PATH="$HOME/arc3_logs/sigil_observer_vector.jsonl"
export SIGIL_BRAILLE_GRAPH_PATH="$HOME/arc3_logs/sigil_braille_graph_trace.jsonl"
export SIGIL_LS20_TEACHER_TRACE_PATH="$HOME/arc3_logs/sigil_ls20_teacher_trace.jsonl"
export SIGIL_LS20_LEARNED_PRIOR_PATH="$HOME/arc3_logs/sigil_arc3_prior_plans_learned.json"
export SIGIL_V27_LS20_TEACHER=1
export SIGIL_LS20_EMBEDDED_PRIOR=1
export SIGIL_LS20_LEARN_FROM_ROUTE=1
export SIGIL_USE_PRIOR_PLAN_CACHE=1
export SIGIL_PRIOR_PLAN_PATH="$HOME/arc3_logs/sigil_arc3_prior_plans.json"
export SIGIL_OBSERVER=1
export SIGIL_BLINDSIGHT=1
export SIGIL_BLINDSIGHT_TRACE=1
export SIGIL_BRAILLE_GRAPH_TRACE=1
export SIGIL_GHOST_SCOUT=1
export SIGIL_MAX_ACTIONS_PER_GAME="${SIGIL_MAX_ACTIONS_PER_GAME:-1800}"
export SIGIL_BFS_SCAN_TIMEOUT="${SIGIL_BFS_SCAN_TIMEOUT:-12}"
export SIGIL_BFS_TIMEOUT="${SIGIL_BFS_TIMEOUT:-300}"
python main.py --agent=myagent --tags=sigil-v27-aggressive-full25-api
