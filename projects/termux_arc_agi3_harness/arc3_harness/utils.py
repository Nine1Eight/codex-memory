from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def now_ts() -> float:
    return time.time()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def append_jsonl(path: str | Path, row: dict[str, Any]) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def frame_array(frame_payload: Any) -> np.ndarray:
    """Return the final 2D frame from ARCEngine FrameData/FrameDataRaw/list payloads."""
    if frame_payload is None:
        return np.zeros((1, 1), dtype=np.int16)
    if hasattr(frame_payload, "frame"):
        frames = frame_payload.frame
    elif isinstance(frame_payload, dict) and "frame" in frame_payload:
        frames = frame_payload["frame"]
    else:
        frames = frame_payload
    if isinstance(frames, np.ndarray):
        arr = frames
    elif isinstance(frames, list) and frames:
        arr = np.asarray(frames[-1])
    else:
        arr = np.zeros((1, 1), dtype=np.int16)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim != 2:
        arr = np.squeeze(arr)
        if arr.ndim != 2:
            arr = np.zeros((1, 1), dtype=np.int16)
    return arr.astype(np.int16, copy=False)


def frame_hash(frame: Any) -> str:
    arr = frame_array(frame)
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()[:16]


def diff_count(a: Any, b: Any) -> int:
    aa, bb = frame_array(a), frame_array(b)
    if aa.shape != bb.shape:
        return int(max(aa.size, bb.size))
    return int(np.sum(aa != bb))


def compact_actions(actions: Iterable[int]) -> str:
    names = {1: "U", 2: "D", 3: "L", 4: "R", 5: "I", 6: "C", 7: "Z", 0: "RESET"}
    parts: list[str] = []
    prev = None
    count = 0
    for a in actions:
        if prev is None:
            prev, count = int(a), 1
        elif int(a) == prev:
            count += 1
        else:
            parts.append(f"{names.get(prev, str(prev))}x{count}" if count > 1 else names.get(prev, str(prev)))
            prev, count = int(a), 1
    if prev is not None:
        parts.append(f"{names.get(prev, str(prev))}x{count}" if count > 1 else names.get(prev, str(prev)))
    return " ".join(parts)
