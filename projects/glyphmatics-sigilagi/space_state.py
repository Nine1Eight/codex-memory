import json
import time
from pathlib import Path

STATE_DIR = Path("space_sessions")
STATE_DIR.mkdir(exist_ok=True)

def _path(session_id):
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:80]
    return STATE_DIR / f"{safe or 'default'}.json"

def load_session(session_id):
    p = _path(session_id)
    if not p.exists():
        return {
            "session_id": session_id,
            "turns": 0,
            "memory": [],
            "history": [],
            "backend_rewards": {},
            "created": time.time(),
            "updated": time.time()
        }

    try:
        return json.loads(p.read_text())
    except Exception:
        return {
            "session_id": session_id,
            "turns": 0,
            "memory": [],
            "history": [],
            "backend_rewards": {},
            "created": time.time(),
            "updated": time.time(),
            "recovered": True
        }

def save_session(state):
    state["updated"] = time.time()
    p = _path(state.get("session_id", "default"))
    p.write_text(json.dumps(state, indent=2))
    return p

def update_session(session_id, user_text, backend, tokens, meta, reply):
    state = load_session(session_id)

    state["turns"] += 1
    state["memory"].extend(tokens[-24:])
    state["memory"] = state["memory"][-256:]

    reward = float(meta.get("score", 0.0))
    stats = state["backend_rewards"].setdefault(
        backend, {"uses": 0, "reward": 0.0, "avg": 0.0}
    )
    stats["uses"] += 1
    stats["reward"] += reward
    stats["avg"] = stats["reward"] / max(1, stats["uses"])

    state["history"].append({
        "time": time.time(),
        "user": user_text,
        "backend": backend,
        "tokens": tokens[-64:],
        "meta": meta,
        "reply": reply
    })
    state["history"] = state["history"][-50:]

    save_session(state)
    return state
