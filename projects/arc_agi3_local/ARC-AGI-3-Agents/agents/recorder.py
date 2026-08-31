import json
import os
import time
from pathlib import Path

class Recorder:
    def __init__(self, prefix="recording", filename=None, guid=None):
        root = Path(os.environ.get("RECORDINGS_DIR", "recordings"))
        root.mkdir(parents=True, exist_ok=True)
        if filename:
            self.filename = str(root / filename)
        else:
            safe = str(prefix).replace("/", "_").replace(" ", "_")
            self.filename = str(root / f"{safe}.{int(time.time())}.recording.jsonl")

    def record(self, obj):
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, default=str) + "\n")
        except Exception:
            pass

    def get(self):
        out = []
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        out.append(json.loads(line))
        except Exception:
            pass
        return out

    @staticmethod
    def list():
        root = Path(os.environ.get("RECORDINGS_DIR", "recordings"))
        if not root.exists():
            return []
        return [p.name for p in root.glob("*.jsonl")]

    @staticmethod
    def get_prefix(name):
        return str(name).split(".")[0]

    @staticmethod
    def get_guid(name):
        parts = str(name).split(".")
        return parts[-3] if len(parts) >= 4 else ""
