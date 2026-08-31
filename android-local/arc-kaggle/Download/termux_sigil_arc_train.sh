#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Sigil Route Agent — Termux ARC-AGI-3 full install + train
# Android/Termux script for real ARC games + local GGUF reasoning
# ============================================================

PROJECT_DIR="${PROJECT_DIR:-$HOME/sigil_route_agent_e2e}"
ZIP_GLOB="${ZIP_GLOB:-*ACTUAL_ARC_GAMES*.zip}"
RUN_DIR="${SIGIL_RUN_DIR:-runs/train_actual_arc_$(date +%Y%m%d_%H%M%S)}"
ONLY_GAME="${SIGIL_ONLY_GAME:-}"
MAX_STEPS="${SIGIL_MAX_STEPS_PER_GAME:-250}"
PLAN_STEPS="${SIGIL_MAX_PLAN_STEPS:-256}"
REASONING_TOKENS="${SIGIL_REASONING_TOKENS:-10000}"
GGUF_MODEL="${SIGIL_GGUF_MODEL:-}"
VLLM_ENABLED="${SIGIL_VLLM_ENABLED:-0}"
OP_MODE="${OPERATION_MODE:-ONLINE}"

print_header() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }
}

print_header "1. Termux packages"
pkg update -y
pkg install -y python clang cmake make git unzip zip rust openssl libffi openblas ndk-sysroot termux-api || true
python -m pip install --upgrade pip setuptools wheel

print_header "2. Python packages"
python -m pip install --upgrade numpy pillow imageio requests pytest
python -m pip install --upgrade arc-agi

if [ "$VLLM_ENABLED" = "1" ]; then
  print_header "3. Installing local GGUF runtime: llama-cpp-python"
  CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" FORCE_CMAKE=1 python -m pip install --upgrade --no-cache-dir llama-cpp-python || {
    echo "llama-cpp-python build failed. Continuing with SIGIL_VLLM_ENABLED=0 fallback."
    export SIGIL_VLLM_ENABLED=0
    VLLM_ENABLED=0
  }
fi

print_header "4. Storage + ZIP discovery"
if [ ! -d "$HOME/storage" ]; then
  termux-setup-storage || true
  echo "If Android asks for storage permission, accept it, then rerun this script."
fi

if [ ! -f "$PROJECT_DIR/agent.py" ]; then
  ZIP_PATH=""
  for base in "$HOME/storage/downloads" "/sdcard/Download" "$HOME"; do
    if [ -d "$base" ]; then
      found="$(find "$base" -maxdepth 3 -type f -name "$ZIP_GLOB" 2>/dev/null | head -n 1 || true)"
      if [ -n "$found" ]; then ZIP_PATH="$found"; break; fi
    fi
  done

  if [ -z "$ZIP_PATH" ]; then
    echo "Could not find ZIP matching: $ZIP_GLOB"
    echo "Download sigil_route_agent_ACTUAL_ARC_GAMES.zip to Android Downloads, then rerun."
    exit 1
  fi

  echo "Found ZIP: $ZIP_PATH"
  rm -rf "$PROJECT_DIR"
  mkdir -p "$PROJECT_DIR"
  unzip -o "$ZIP_PATH" -d "$PROJECT_DIR"
else
  echo "Project already exists: $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

print_header "5. Verify base layout"
find . -maxdepth 3 -type f | sort | grep -E "agent.py|arc_sigil_agent.py|planner.py|run_actual_arc_games.py" || true
[ -f kaggle_adapter/arc_sigil_agent.py ] || { echo "Missing kaggle_adapter/arc_sigil_agent.py"; exit 1; }
[ -f sigil_route_agent/agent.py ] || { echo "Missing sigil_route_agent/agent.py"; exit 1; }
[ -f sigil_route_agent/planner.py ] || { echo "Missing sigil_route_agent/planner.py"; exit 1; }

print_header "6. Apply high-level training patches"
cat > sigil_route_agent/vllm_adapter.py <<'PY'
from __future__ import annotations
import json, os, re
from typing import Any, Dict

class LocalGGUFVLLM:
    def __init__(self):
        self.enabled = os.getenv("SIGIL_VLLM_ENABLED", "0") == "1"
        self.model_path = os.getenv("SIGIL_GGUF_MODEL", "")
        self.ctx = int(os.getenv("SIGIL_GGUF_CTX", "8192"))
        self.threads = int(os.getenv("SIGIL_GGUF_THREADS", "4"))
        self.max_tokens = int(os.getenv("SIGIL_GGUF_MAX_TOKENS", "384"))
        self.temperature = float(os.getenv("SIGIL_GGUF_TEMP", "0.1"))
        self.llm = None
        self.error = None
        if self.enabled:
            self._load()

    def _load(self):
        if not self.model_path or not os.path.exists(self.model_path):
            self.error = f"GGUF model not found: {self.model_path}"
            self.enabled = False
            return
        try:
            from llama_cpp import Llama
            self.llm = Llama(model_path=self.model_path, n_ctx=self.ctx, n_threads=self.threads, verbose=False)
        except Exception as exc:
            self.error = repr(exc)
            self.enabled = False

    def advise_action(self, *, state_sigil: str, plan_actions: list[str], planner_reason: str,
                      confidence: float, legal_actions: list[str], action_history: list[str],
                      transition_memory: list[dict]) -> Dict[str, Any]:
        if not self.enabled or self.llm is None:
            return {"enabled": False, "error": self.error, "suggested_intent": None, "mode": "disabled"}
        prompt = self._prompt(state_sigil, plan_actions, planner_reason, confidence, legal_actions, action_history, transition_memory)
        try:
            out = self.llm(prompt, max_tokens=self.max_tokens, temperature=self.temperature, stop=["</json>", "\n\n\n"])
            text = out["choices"][0]["text"]
            parsed = self._parse_json(text)
            parsed["enabled"] = True
            parsed["raw"] = text[:1200]
            return parsed
        except Exception as exc:
            return {"enabled": False, "error": repr(exc), "suggested_intent": None, "mode": "runtime_error"}

    def _prompt(self, state_sigil, plan_actions, planner_reason, confidence, legal_actions, action_history, transition_memory):
        return f"""
You are a local GGUF reasoning module inside an ARC-AGI-3 agent.
Output JSON only. Choose useful exploration/action intent.
Valid intents: UP, DOWN, LEFT, RIGHT, ACT, CLICK, WAIT, EXPLORE.
Rules:
- If planner_reason is no_agent_or_goal, do not choose WAIT.
- If recent actions repeat, choose a different exploratory action.
- If legal actions are ACTION5/ACTION6/ACTION7, prefer ACTION6 or ACTION7 over repeated ACTION5 unless ACTION5 changed state.

state_sigil={state_sigil[:4000]}
planner_reason={planner_reason}
confidence={confidence}
plan_actions={plan_actions[:32]}
legal_actions={legal_actions}
action_history={action_history[-24:]}
transition_memory={json.dumps(transition_memory[-12:], default=str)[:4000]}

Return JSON exactly:
{{"suggested_intent":"ACT","arc_preference":"ACTION6","reason":"short","mode":"local_gguf"}}
</json>
""".strip()

    def _parse_json(self, text):
        m = re.search(r"\{.*\}", text.strip(), flags=re.S)
        if not m:
            return {"suggested_intent": "EXPLORE", "arc_preference": None, "reason": "no_json", "mode": "parse_fallback"}
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return {"suggested_intent": "EXPLORE", "arc_preference": None, "reason": "bad_json", "mode": "parse_fallback"}
        intent = str(obj.get("suggested_intent", "EXPLORE")).upper()
        if intent not in {"UP","DOWN","LEFT","RIGHT","ACT","CLICK","WAIT","EXPLORE"}:
            intent = "EXPLORE"
        return {"suggested_intent": intent, "arc_preference": obj.get("arc_preference"), "reason": str(obj.get("reason", ""))[:300], "mode": str(obj.get("mode", "local_gguf"))}

class VLLMAdapter(LocalGGUFVLLM):
    pass
PY

cat > sigil_route_agent/agent.py <<'PY'
from __future__ import annotations
from typing import Any, Dict, List
from .frame_grid import FrameGridExtractor
from .rules import RuleInducer
from .planner import RoutePlanner
from .simulator import WorldModelSimulator
from .contemplation import ContemplationCore
from .reality_checker import RealityChecker
from .vllm_adapter import VLLMAdapter

class SigilRouteAgent:
    def __init__(self, contemplation_budget_tokens: int = 10000, max_plan_steps: int = 256, **kwargs):
        self.extractor = FrameGridExtractor()
        self.rules = RuleInducer()
        self.planner = RoutePlanner(max_steps=max_plan_steps)
        self.sim = WorldModelSimulator()
        self.contemplation = ContemplationCore(token_budget=contemplation_budget_tokens)
        self.reality = RealityChecker()
        self.vllm = VLLMAdapter()
        self.previous_state = None
        self.previous_prediction = None
        self.action_history: List[str] = []
        self.transition_memory: List[Dict[str, Any]] = []

    def reset(self):
        self.previous_state = None
        self.previous_prediction = None
        self.action_history = []
        self.transition_memory = []

    def act_from_frame(self, frame=None, step_index: int = 0, previous_action=None, legal_actions=None, **kwargs):
        state = self._extract_state(frame, step_index)
        state_sigil = state.sigil() if hasattr(state, "sigil") else str(state)
        rules = self.rules.get_rules() if hasattr(self.rules, "get_rules") else []
        plan = self.planner.plan(state, rules)
        plan_actions = list(getattr(plan, "actions", []) or [])
        confidence = float(getattr(plan, "confidence", 0.0) or 0.0)
        reason = str(getattr(plan, "reason", ""))
        symbolic_action = plan_actions[0] if plan_actions else "EXPLORE"
        uncertain = confidence < 0.5 or reason in {"no_agent_or_goal", "fallback_wait"} or symbolic_action == "WAIT"
        vllm_advice = None
        if uncertain:
            vllm_advice = self.vllm.advise_action(
                state_sigil=state_sigil, plan_actions=plan_actions, planner_reason=reason,
                confidence=confidence, legal_actions=legal_actions or [],
                action_history=self.action_history, transition_memory=self.transition_memory)
            suggested = vllm_advice.get("suggested_intent") if isinstance(vllm_advice, dict) else None
            if suggested and suggested != "WAIT":
                symbolic_action = str(suggested).upper()
            else:
                symbolic_action = self._explore_intent()
        predicted_next = self.sim.step(state, symbolic_action, rules)
        self.previous_state = state
        self.previous_prediction = predicted_next
        self.action_history.append(symbolic_action)
        return {
            "action": symbolic_action,
            "state_sigil": state_sigil,
            "plan_actions": plan_actions,
            "confidence": confidence,
            "reason": reason,
            "uncertain": uncertain,
            "vllm": vllm_advice,
            "contemplation": self.contemplation.summarize(state, rules, plan),
            "predicted_next_sigil": predicted_next.sigil() if hasattr(predicted_next, "sigil") else str(predicted_next),
        }

    def act(self, frame=None, **kwargs):
        return self.act_from_frame(frame, **kwargs)

    def _extract_state(self, frame, step_index: int):
        if hasattr(self.extractor, "extract"):
            return self.extractor.extract(frame, frame_id=step_index)
        if hasattr(self.extractor, "frame_to_state"):
            return self.extractor.frame_to_state(frame, frame_id=step_index)
        raise RuntimeError("FrameGridExtractor has no extract/frame_to_state method")

    def _explore_intent(self) -> str:
        cycle = ["ACT", "CLICK", "UP", "DOWN", "LEFT", "RIGHT"]
        return cycle[len(self.action_history) % len(cycle)]
PY

cat > kaggle_adapter/arc_sigil_agent.py <<'PY'
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
try:
    from arcengine import GameAction
except Exception:
    GameAction = None
from sigil_route_agent.agent import SigilRouteAgent

@dataclass
class ArcSigilConfig:
    max_plan_steps: int = 256
    contemplation_budget_tokens: int = 10000
    save_debug: bool = True
    safe_fallback: bool = True

class ArcSigilAgent:
    SYMBOLIC_TO_ARC_PREFS = {
        "UP": ["UP", "ACTION1", "NORTH", "W"],
        "DOWN": ["DOWN", "ACTION2", "SOUTH", "S"],
        "LEFT": ["LEFT", "ACTION3", "WEST", "A"],
        "RIGHT": ["RIGHT", "ACTION4", "EAST", "D"],
        "WAIT": ["ACTION6", "ACTION7", "ACTION5", "WAIT", "NOOP", "NO_OP"],
        "ACT": ["ACT", "USE", "INTERACT", "ACTION6", "ACTION7", "ACTION5"],
        "CLICK": ["CLICK", "TAP", "ACTION7", "ACTION6", "ACTION5"],
        "EXPLORE": ["ACTION6", "ACTION7", "ACTION5", "ACTION1", "ACTION2", "ACTION3", "ACTION4"],
    }

    def __init__(self, config: Optional[ArcSigilConfig] = None):
        self.config = config or ArcSigilConfig()
        self.agent = SigilRouteAgent(contemplation_budget_tokens=self.config.contemplation_budget_tokens, max_plan_steps=self.config.max_plan_steps)
        self.step_index = 0
        self.last_action_name = None
        self.last_decision = None
        self.last_action_space: List[str] = []

    def reset(self):
        self.agent.reset()
        self.step_index = 0
        self.last_action_name = None
        self.last_decision = None
        self.last_action_space = []

    def act(self, obs: Any, env: Any = None):
        frame = self._extract_frame(obs, env)
        legal = self._legal_actions(env)
        legal_names = [self._name(a) for a in legal]
        decision = self.agent.act_from_frame(frame=frame, step_index=self.step_index, previous_action=self.last_action_name, legal_actions=legal_names)
        symbolic_intent = str(decision.get("action", "EXPLORE")).upper()
        action, data, action_debug = self._resolve_legal_action(symbolic_intent, env, decision)
        reasoning = {
            "agent": "sigil_route_agent_actual_arc_full",
            "step_index": self.step_index,
            "got_actual_frame": frame is not None,
            "symbolic_intent": symbolic_intent,
            "arc_action": self._name(action),
            "action_data": data,
            "action_debug": action_debug,
            "state_sigil": self._compact(decision.get("state_sigil", "")),
            "plan_actions": decision.get("plan_actions", [])[:64],
            "confidence": decision.get("confidence"),
            "reason": decision.get("reason"),
            "vllm": decision.get("vllm"),
        }
        self.last_decision = reasoning
        self.last_action_name = self._name(action)
        self.step_index += 1
        return action, data, reasoning

    def _resolve_legal_action(self, symbolic_intent, env, decision):
        legal = self._legal_actions(env)
        legal_names = [self._name(a) for a in legal]
        self.last_action_space = legal_names
        debug = {"symbolic_intent": symbolic_intent, "legal_actions": legal_names, "mode": None}
        arc_pref = None
        vllm = decision.get("vllm") if isinstance(decision, dict) else None
        if isinstance(vllm, dict):
            arc_pref = vllm.get("arc_preference")
        pref_names = []
        if arc_pref:
            pref_names.append(str(arc_pref).upper())
        pref_names += self.SYMBOLIC_TO_ARC_PREFS.get(symbolic_intent, [])
        for pref in pref_names:
            for candidate in legal:
                if self._name(candidate).upper() == str(pref).upper():
                    debug.update({"mode": "intent_or_vllm_to_legal", "selected": self._name(candidate), "arc_pref": arc_pref})
                    return candidate, self._build_action_data(candidate, decision), debug
        non_reset = [a for a in legal if "RESET" not in self._name(a).upper()]
        if non_reset:
            selected = non_reset[self.step_index % len(non_reset)]
            debug.update({"mode": "round_robin_legal_exploration", "selected": self._name(selected)})
            return selected, self._build_action_data(selected, decision), debug
        if GameAction is not None:
            for name in ("ACTION1","ACTION2","ACTION3","ACTION4","ACTION5","ACTION6","ACTION7"):
                if hasattr(GameAction, name):
                    selected = getattr(GameAction, name)
                    debug.update({"mode": "enum_last_resort", "selected": name})
                    return selected, {}, debug
        debug.update({"mode": "string_last_resort", "selected": "ACTION1"})
        return "ACTION1", {}, debug

    def _legal_actions(self, env):
        if env is None: return []
        try: actions = list(env.action_space or [])
        except Exception: return []
        return [a[0] if isinstance(a, (tuple, list)) and a else a for a in actions]

    def _build_action_data(self, action, decision):
        name = self._name(action).upper()
        if "CLICK" in name or "TAP" in name:
            target = decision.get("target_cell") or decision.get("goal_cell")
            if isinstance(target, (list, tuple)) and len(target) >= 2:
                return {"x": int(target[0]), "y": int(target[1])}
            return {"x": 32, "y": 32}
        return {}

    def _extract_frame(self, obs, env=None):
        candidates = []
        if obs is not None:
            candidates.append(obs)
            for attr in ("frame","image","rgb","pixels","observation","data"):
                if hasattr(obs, attr):
                    try: candidates.append(getattr(obs, attr))
                    except Exception: pass
            if isinstance(obs, dict):
                for key in ("frame","image","rgb","pixels","observation","data"):
                    if key in obs: candidates.append(obs[key])
        if env is not None:
            for attr in ("observation_space","last_observation","observation","frame","image"):
                if hasattr(env, attr):
                    try: candidates.append(getattr(env, attr))
                    except Exception: pass
            if hasattr(env, "render"):
                try: candidates.append(env.render())
                except Exception: pass
        for item in candidates:
            arr = self._to_numpy_rgb(item)
            if arr is not None: return arr
        return None

    def _to_numpy_rgb(self, item):
        if item is None: return None
        for attr in ("frame","image","rgb","pixels","data"):
            if hasattr(item, attr):
                try:
                    arr = self._to_numpy_rgb(getattr(item, attr))
                    if arr is not None: return arr
                except Exception: pass
        try: arr = np.asarray(item)
        except Exception: return None
        if arr.ndim == 2: arr = np.stack([arr, arr, arr], axis=-1)
        if arr.ndim == 3 and arr.shape[-1] >= 3: return arr[..., :3].astype(np.uint8)
        return None

    def _name(self, action): return str(getattr(action, "name", action))
    def _compact(self, value, max_chars=4000):
        text = str(value)
        return text[:max_chars] + f"...<truncated:{len(text)}>" if len(text) > max_chars else text
PY

cat > run_full_actual_arc.py <<'PY'
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Any, Dict, Tuple
import arc_agi
from arc_agi import OperationMode
try:
    from arcengine import GameState
except Exception:
    GameState = None
from kaggle_adapter.arc_sigil_agent import ArcSigilAgent, ArcSigilConfig

def get_mode():
    raw = os.getenv("OPERATION_MODE", "ONLINE").upper()
    return OperationMode.COMPETITION if raw == "COMPETITION" else OperationMode.OFFLINE if raw == "OFFLINE" else OperationMode.ONLINE

def discover_games(arc):
    only = os.getenv("SIGIL_ONLY_GAME")
    if only: return [only]
    for name in ("get_environments", "get_environment_ids", "list_environments"):
        if hasattr(arc, name):
            envs = getattr(arc, name)()
            if envs: return [str(e) for e in envs]
    raise RuntimeError("No ARC environments discovered")

def safe_json(obj):
    try:
        json.dumps(obj, default=str); return obj
    except Exception: return str(obj)

def compact_debug(obj, max_chars=8000):
    try: text = json.dumps(obj, default=str)
    except Exception: text = str(obj)
    if len(text) > max_chars:
        return {"truncated": True, "chars": len(text), "preview": text[:max_chars]}
    try: return json.loads(text)
    except Exception: return text[:max_chars]

def action_name(action): return getattr(action, "name", str(action))

def normalize_agent_output(output):
    if isinstance(output, dict):
        return output.get("arc_action") or output.get("action"), output.get("data") or output.get("action_data") or {}, output.get("reasoning") or output
    if isinstance(output, (tuple, list)):
        if len(output) >= 3: return output[0], output[1] if isinstance(output[1], dict) else {}, output[2] if isinstance(output[2], dict) else {"reasoning": str(output[2])}
        if len(output) == 2: return output[0], output[1] if isinstance(output[1], dict) else {}, {}
        if len(output) == 1: return output[0], {}, {}
    return output, {}, {}

def legalize_action(action, data, reasoning, env):
    try: legal = list(env.action_space or [])
    except Exception: legal = []
    if not legal: return action, data, reasoning
    if action in legal: return action, data, reasoning
    wanted = action_name(action)
    for c in legal:
        if action_name(c) == wanted: return c, data, reasoning
    non_reset = [a for a in legal if "RESET" not in action_name(a).upper()]
    fallback = non_reset[0] if non_reset else legal[0]
    r = dict(reasoning or {})
    r["fallback"] = {"original_action": wanted, "fallback_action": action_name(fallback), "legal_actions": [action_name(a) for a in legal]}
    return fallback, {}, r

def extract_action_packet(runner, obs, env, step):
    t0 = time.time()
    raw = runner.act(obs, env)
    action, data, reasoning = normalize_agent_output(raw)
    action, data, reasoning = legalize_action(action, data, reasoning, env)
    last = getattr(runner, "last_decision", reasoning)
    packet = {"agent": "sigil_route_agent_train", "step_index": step, "arc_action": action_name(action), "action_data": data, "elapsed_agent_sec": round(time.time()-t0, 4), "decision": compact_debug(last)}
    return action, data, packet

def get_initial_obs(env):
    for attr in ("observation_space", "last_observation", "observation"):
        if hasattr(env, attr):
            try:
                val = getattr(env, attr)
                if val is not None: return val
            except Exception: pass
    return None

def terminal(state):
    s = str(state).upper()
    return "WIN" in s or "GAME_OVER" in s

def play_game(arc, game_id, out_root, max_steps):
    game_out = out_root / game_id; game_out.mkdir(parents=True, exist_ok=True)
    print(f"[MAKE] game={game_id}", flush=True)
    env = arc.make(game_id, render_mode=os.getenv("SIGIL_RENDER_MODE") or None)
    runner = ArcSigilAgent(ArcSigilConfig(max_plan_steps=int(os.getenv("SIGIL_MAX_PLAN_STEPS", "256")), contemplation_budget_tokens=int(os.getenv("SIGIL_REASONING_TOKENS", "10000")), save_debug=True, safe_fallback=True))
    runner.reset(); obs = get_initial_obs(env)
    rows=[]; status="running"
    for step in range(max_steps):
        try: action, data, reasoning = extract_action_packet(runner, obs, env, step)
        except Exception as exc:
            rows.append({"schema":"sigil_train_arc_transition.v3","game_id":game_id,"step":step,"status":"agent_failed","error":repr(exc)}); status="agent_failed"; break
        print(f"[ARC_STEP] game={game_id} step={step} action={action_name(action)} data={data}", flush=True)
        try:
            try: next_obs = env.step(action, data=data, reasoning=reasoning)
            except TypeError: next_obs = env.step(action, data) if data else env.step(action)
        except Exception as exc:
            rows.append({"schema":"sigil_train_arc_transition.v3","game_id":game_id,"step":step,"action":action_name(action),"data":safe_json(data),"status":"step_failed","error":repr(exc),"reasoning":compact_debug(reasoning)}); status="step_failed"; break
        state = getattr(next_obs, "state", None); score = getattr(next_obs, "score", None)
        row={"schema":"sigil_train_arc_transition.v3","game_id":game_id,"step":step,"action":action_name(action),"data":safe_json(data),"state":str(state),"score":safe_json(score),"levels_completed":safe_json(getattr(next_obs,"levels_completed",None)),"reasoning":compact_debug(reasoning),"status":"ok"}
        rows.append(row); obs = next_obs
        # feed memory back into local core
        try: runner.agent.transition_memory.append(row)
        except Exception: pass
        if (GameState is not None and state in (GameState.WIN, GameState.GAME_OVER)) or terminal(state): status=str(state); break
    if status == "running": status="max_steps_reached"
    (game_out/"transitions.jsonl").write_text("\n".join(json.dumps(r, default=str) for r in rows)+"\n")
    summary={"game_id":game_id,"status":status,"steps":len(rows),"out":str(game_out),"last":rows[-1] if rows else None}
    (game_out/"summary.json").write_text(json.dumps(summary, indent=2, default=str)); return summary

def main():
    out_root=Path(os.getenv("SIGIL_RUN_DIR", "runs/train_actual_arc")); out_root.mkdir(parents=True, exist_ok=True)
    max_steps=int(os.getenv("SIGIL_MAX_STEPS_PER_GAME", "250")); mode=get_mode()
    cfg={"mode":str(mode),"max_steps_per_game":max_steps,"reasoning_tokens":os.getenv("SIGIL_REASONING_TOKENS","10000"),"max_plan_steps":os.getenv("SIGIL_MAX_PLAN_STEPS","256"),"vllm_enabled":os.getenv("SIGIL_VLLM_ENABLED","0"),"gguf_model":os.getenv("SIGIL_GGUF_MODEL"),"only_game":os.getenv("SIGIL_ONLY_GAME"),"run_dir":str(out_root)}
    print(json.dumps(cfg, indent=2), flush=True)
    arc=arc_agi.Arcade(operation_mode=mode); games=discover_games(arc)
    summaries=[]
    for gid in games:
        try: summaries.append(play_game(arc, gid, out_root, max_steps))
        except Exception as exc: summaries.append({"game_id":gid,"status":"make_or_run_failed","error":repr(exc),"steps":0})
    try: scorecard=arc.get_scorecard()
    except Exception as exc: scorecard={"error":repr(exc)}
    result={"config":cfg,"summaries":summaries,"scorecard":safe_json(scorecard)}
    (out_root/"run_summary.json").write_text(json.dumps(result, indent=2, default=str)); print(json.dumps(result, indent=2, default=str), flush=True)
if __name__ == "__main__": main()
PY

find . -type d -name "__pycache__" -prune -exec rm -rf {} +

print_header "7. Import test"
python - <<'PY'
from kaggle_adapter.arc_sigil_agent import ArcSigilAgent
from sigil_route_agent.agent import SigilRouteAgent
from sigil_route_agent.vllm_adapter import VLLMAdapter
print("OK imports")
v=VLLMAdapter(); print("GGUF enabled:", v.enabled, "error:", v.error)
PY

print_header "8. ARC API key check"
if [ -z "${ARC_API_KEY:-}" ]; then
  echo "ARC_API_KEY is not set. Set it without pasting it in chat:"
  echo 'export ARC_API_KEY="YOUR_NEW_ROTATED_KEY"'
  exit 1
fi
python - <<'PY'
import os
k=os.getenv("ARC_API_KEY")
print("ARC_API_KEY set:", bool(k), "prefix:", k[:6] if k else None, "len:", len(k) if k else 0)
PY

print_header "9. Run real ARC training"
export OPERATION_MODE="$OP_MODE"
export SIGIL_VLLM_ENABLED="$VLLM_ENABLED"
if [ -n "$GGUF_MODEL" ]; then export SIGIL_GGUF_MODEL="$GGUF_MODEL"; fi
export SIGIL_FULL_PIPELINE=1
export SIGIL_ENABLE_PREDICTION=1
export SIGIL_ENABLE_TRAINING_LOG=1
export SIGIL_ENABLE_REALITY_CHECK=1
export SIGIL_MAX_STEPS_PER_GAME="$MAX_STEPS"
export SIGIL_REASONING_TOKENS="$REASONING_TOKENS"
export SIGIL_MAX_PLAN_STEPS="$PLAN_STEPS"
export SIGIL_RUN_DIR="$RUN_DIR"
if [ -n "$ONLY_GAME" ]; then export SIGIL_ONLY_GAME="$ONLY_GAME"; else unset SIGIL_ONLY_GAME || true; fi

python run_full_actual_arc.py

print_header "10. Output"
echo "Run dir: $PROJECT_DIR/$RUN_DIR"
find "$RUN_DIR" -maxdepth 3 -type f | sort
