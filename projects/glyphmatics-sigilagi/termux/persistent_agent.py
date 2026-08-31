#!/usr/bin/env python3
from pathlib import Path
from collections import deque, defaultdict
import json
import time

STATE_PATH = Path("agent_state.json")

DEFAULT_STATE = {
    "turns": 0,
    "memory_tokens": [],
    "backend_stats": {},
    "last_backend": "trainable",
    "auto_backend": False,
    "mode": None,
    "sessions": []
}

def load_agent_state():
    if not STATE_PATH.exists():
        return dict(DEFAULT_STATE)

    try:
        data = json.loads(STATE_PATH.read_text())
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_STATE)

def save_agent_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))

def make_memory(maxlen=256):
    state = load_agent_state()
    return deque(state.get("memory_tokens", [])[-maxlen:], maxlen=maxlen)

def make_backend_stats():
    state = load_agent_state()
    return defaultdict(
        lambda: {"uses": 0, "reward": 0.0, "avg": 0.0},
        state.get("backend_stats", {})
    )

def persist_runtime(memory, backend_stats, last_backend, auto_backend, mode=None):
    state = load_agent_state()
    state["turns"] = int(state.get("turns", 0)) + 1
    state["memory_tokens"] = list(memory)[-256:]
    state["backend_stats"] = dict(backend_stats)
    state["last_backend"] = last_backend
    state["auto_backend"] = bool(auto_backend)
    state["mode"] = mode
    state["last_saved"] = time.time()
    save_agent_state(state)

def log_turn(user, reply, backend, meta):
    log = Path("chat_memory.jsonl")
    with log.open("a") as f:
        f.write(json.dumps({
            "time": time.time(),
            "user": user,
            "reply": reply,
            "backend": backend,
            "meta": meta
        }) + "\n")
