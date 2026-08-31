import json, hashlib, time
from pathlib import Path

STATE_FILE = Path("termux/agent_state.json")

def save_state(state):
    payload = {
        "version": 1,
        "timestamp": time.time(),
        "state": state
    }
    raw = json.dumps(payload, sort_keys=True).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    STATE_FILE.write_text(json.dumps(payload, indent=2))

def load_state():
    if not STATE_FILE.exists():
        return None
    payload = json.loads(STATE_FILE.read_text())
    chk = payload.get("sha256")
    raw = json.dumps({
        "version": payload["version"],
        "timestamp": payload["timestamp"],
        "state": payload["state"]
    }, sort_keys=True).encode()

    if hashlib.sha256(raw).hexdigest() != chk:
        print("[STATE CORRUPTION DETECTED]")
        return None

    return payload["state"]
