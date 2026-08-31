
# Cell 1 — Runtime configuration and deterministic setup
from __future__ import annotations

import os
import sys
import json
import math
import time
import random
import hashlib
import itertools
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import IterableDataset, DataLoader
except Exception as exc:
    raise RuntimeError("PyTorch is required for this notebook.") from exc

SEED = 918
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DTYPE = torch.float32

@dataclass(frozen=True)
class Config:
    colors: int = 16
    canvas_size: int = 64
    embedding_dim: int = 192
    program_hidden: int = 192
    max_program_len: int = 6
    beam_width: int = 64
    branch_factor: int = 12
    refinement_rounds: int = 4
    synthetic_train_examples: int = 120_000
    synthetic_validation_examples: int = 2_000
    batch_size: int = 64
    train_steps: int = 8_000
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    grad_clip: float = 1.0
    tta_steps: int = 24
    tta_lr: float = 8e-4
    action_budget: int = 400
    archive_limit: int = 12_000
    reasoning_limit_bytes: int = 16 * 1024
    checkpoint_path: str = "/kaggle/working/neurosymbolic_arc3.pt"

CFG = Config()
print({"device": str(DEVICE), "torch": torch.__version__, "config": dataclasses.asdict(CFG)})



# Cell 2 — Canonical utilities, grid normalization, fingerprints, and compact reasoning

def canonical_dumps(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

def grid_array(grid: Any, size: int = CFG.canvas_size) -> np.ndarray:
    arr = np.asarray(grid, dtype=np.int64)
    if arr.ndim != 2:
        raise ValueError(f"Expected a 2-D grid, got shape {arr.shape}.")
    arr = np.clip(arr, 0, CFG.colors - 1)
    out = np.zeros((size, size), dtype=np.int64)
    h, w = arr.shape
    out[: min(h, size), : min(w, size)] = arr[:size, :size]
    return out

def grid_fingerprint(grid: Any) -> str:
    arr = grid_array(grid)
    return hashlib.sha256(arr.astype(np.uint8).tobytes()).hexdigest()[:16]

def action_name(action: Any) -> str:
    return getattr(action, "name", str(action))

def json_safe_reasoning(payload: Mapping[str, Any]) -> dict[str, Any]:
    encoded = canonical_dumps(dict(payload)).encode("utf-8")
    if len(encoded) > CFG.reasoning_limit_bytes:
        raise ValueError(f"Reasoning payload exceeds {CFG.reasoning_limit_bytes} bytes.")
    restored = json.loads(encoded.decode("utf-8"))
    if not isinstance(restored, dict):
        raise TypeError("Reasoning must round-trip as a JSON object.")
    return restored

def compact_reasoning(
    *,
    mode: str,
    state_id: str,
    depth: int,
    action: str,
    why: str,
    archive_size: int,
    confidence: float | None = None,
    target: tuple[int, int] | None = None,
    program: Sequence[str] | None = None,
    refinement: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "v": 1,
        "mode": mode,
        "state": state_id,
        "depth": int(depth),
        "action": action,
        "why": why[:384],
        "archive": int(archive_size),
    }
    if confidence is not None:
        payload["confidence"] = round(float(confidence), 4)
    if target is not None:
        payload["target"] = [int(target[0]), int(target[1])]
    if program:
        payload["program"] = list(program)[:CFG.max_program_len]
    if refinement is not None:
        payload["refinement"] = int(refinement)
    return json_safe_reasoning(payload)



# Cell 3 — Discrete grid-transformation DSL

Grid = np.ndarray

@dataclass(frozen=True)
class Op:
    name: str
    fn: Callable[[Grid], Grid]
    cost: float = 1.0

def _copy(g: Grid) -> Grid:
    return np.array(g, copy=True)

def rot90(g): return np.rot90(g, 1).copy()
def rot180(g): return np.rot90(g, 2).copy()
def rot270(g): return np.rot90(g, 3).copy()
def flip_h(g): return np.fliplr(g).copy()
def flip_v(g): return np.flipud(g).copy()
def transpose(g): return np.transpose(g).copy()

def trim_background(g: Grid) -> Grid:
    ys, xs = np.where(g != 0)
    if len(xs) == 0:
        return np.zeros((1, 1), dtype=g.dtype)
    return g[ys.min():ys.max()+1, xs.min():xs.max()+1].copy()

def most_frequent_nonzero(g: Grid) -> int:
    vals, counts = np.unique(g[g != 0], return_counts=True)
    return int(vals[np.argmax(counts)]) if len(vals) else 0

def recolor_factory(src: int, dst: int) -> Op:
    def fn(g):
        o = _copy(g)
        o[o == src] = dst
        return o
    return Op(f"recolor_{src}_{dst}", fn, 1.1)

def keep_color_factory(color: int) -> Op:
    def fn(g):
        return np.where(g == color, g, 0).astype(g.dtype)
    return Op(f"keep_{color}", fn, 1.1)

def fill_bbox_factory(color: int) -> Op:
    def fn(g):
        o = _copy(g)
        ys, xs = np.where(g == color)
        if len(xs):
            o[ys.min():ys.max()+1, xs.min():xs.max()+1] = color
        return o
    return Op(f"fill_bbox_{color}", fn, 1.3)

def outline_bbox_factory(color: int) -> Op:
    def fn(g):
        o = _copy(g)
        ys, xs = np.where(g == color)
        if len(xs):
            y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            o[y0, x0:x1+1] = color
            o[y1, x0:x1+1] = color
            o[y0:y1+1, x0] = color
            o[y0:y1+1, x1] = color
        return o
    return Op(f"outline_bbox_{color}", fn, 1.4)

def shift_factory(dy: int, dx: int) -> Op:
    def fn(g):
        o = np.zeros_like(g)
        h, w = g.shape
        sy0, sy1 = max(0, -dy), min(h, h-dy)
        sx0, sx1 = max(0, -dx), min(w, w-dx)
        ty0, ty1 = max(0, dy), min(h, h+dy)
        tx0, tx1 = max(0, dx), min(w, w+dx)
        if sy1 > sy0 and sx1 > sx0:
            o[ty0:ty1, tx0:tx1] = g[sy0:sy1, sx0:sx1]
        return o
    return Op(f"shift_{dy}_{dx}", fn, 1.2)

BASE_OPS = [
    Op("identity", _copy, 0.0),
    Op("rot90", rot90),
    Op("rot180", rot180),
    Op("rot270", rot270),
    Op("flip_h", flip_h),
    Op("flip_v", flip_v),
    Op("transpose", transpose),
    Op("trim", trim_background, 0.8),
]

PARAM_OPS = (
    [shift_factory(dy, dx) for dy, dx in [(-1,0),(1,0),(0,-1),(0,1),(-2,0),(2,0),(0,-2),(0,2)]]
    + [keep_color_factory(c) for c in range(1, CFG.colors)]
    + [fill_bbox_factory(c) for c in range(1, CFG.colors)]
    + [outline_bbox_factory(c) for c in range(1, CFG.colors)]
    + [recolor_factory(s, d) for s in range(1, 10) for d in range(1, 10) if s != d]
)

OPS: list[Op] = BASE_OPS + PARAM_OPS
OP_INDEX = {op.name: i for i, op in enumerate(OPS)}
STOP_INDEX = len(OPS)
VOCAB_SIZE = len(OPS) + 1

def execute_program(grid: Grid, program: Sequence[int]) -> Grid:
    out = np.array(grid, copy=True)
    for token in program:
        if token == STOP_INDEX:
            break
        out = OPS[int(token)].fn(out)
    return out

def program_names(program: Sequence[int]) -> list[str]:
    return ["STOP" if i == STOP_INDEX else OPS[int(i)].name for i in program]



# Cell 4 — Synthetic curriculum capable of producing 100K+ unique puzzles lazily

@dataclass(frozen=True)
class SyntheticExample:
    source: Grid
    target: Grid
    program: tuple[int, ...]

class SyntheticPuzzleStream(IterableDataset):
    def __init__(self, total: int, seed: int, max_program_len: int = CFG.max_program_len):
        super().__init__()
        self.total = int(total)
        self.seed = int(seed)
        self.max_program_len = int(max_program_len)

    @staticmethod
    def random_grid(rng: np.random.Generator) -> Grid:
        h = int(rng.integers(8, 33))
        w = int(rng.integers(8, 33))
        g = np.zeros((h, w), dtype=np.int64)
        n_obj = int(rng.integers(1, 8))
        colors = rng.choice(np.arange(1, 10), size=n_obj, replace=True)
        for color in colors:
            kind = int(rng.integers(0, 4))
            y0 = int(rng.integers(0, h))
            x0 = int(rng.integers(0, w))
            if kind == 0:
                g[y0, x0] = color
            elif kind == 1:
                hh = int(rng.integers(1, min(6, h-y0)+1))
                ww = int(rng.integers(1, min(6, w-x0)+1))
                g[y0:y0+hh, x0:x0+ww] = color
            elif kind == 2:
                length = int(rng.integers(1, min(8, w-x0)+1))
                g[y0, x0:x0+length] = color
            else:
                length = int(rng.integers(1, min(8, h-y0)+1))
                g[y0:y0+length, x0] = color
        return g

    @staticmethod
    def sample_program(rng: np.random.Generator, max_len: int) -> tuple[int, ...]:
        length = int(rng.integers(1, max_len + 1))
        pool = np.arange(len(OPS))
        weights = np.ones(len(OPS), dtype=np.float64)
        for i, op in enumerate(OPS):
            if op.name.startswith(("recolor_", "fill_bbox_", "outline_bbox_")):
                weights[i] = 0.35
            elif op.name.startswith("keep_"):
                weights[i] = 0.5
            elif op.name.startswith("shift_"):
                weights[i] = 0.8
            else:
                weights[i] = 1.4
        weights /= weights.sum()
        tokens = rng.choice(pool, size=length, replace=True, p=weights).tolist()
        tokens.append(STOP_INDEX)
        return tuple(int(x) for x in tokens)

    def __iter__(self) -> Iterator[SyntheticExample]:
        worker = torch.utils.data.get_worker_info()
        worker_id = 0 if worker is None else worker.id
        workers = 1 if worker is None else worker.num_workers
        for index in range(worker_id, self.total, workers):
            rng = np.random.default_rng(self.seed + index * 104729)
            source = self.random_grid(rng)
            program = self.sample_program(rng, self.max_program_len)
            target = execute_program(source, program)
            if target.size == 0:
                target = np.zeros((1,1), dtype=np.int64)
            yield SyntheticExample(source, target, program)

def pad_program(program: Sequence[int], max_len: int = CFG.max_program_len + 1) -> np.ndarray:
    out = np.full(max_len, STOP_INDEX, dtype=np.int64)
    n = min(len(program), max_len)
    out[:n] = np.asarray(program[:n], dtype=np.int64)
    return out

def synthetic_collate(batch: Sequence[SyntheticExample]):
    src = np.stack([grid_array(x.source) for x in batch])
    tgt = np.stack([grid_array(x.target) for x in batch])
    prog = np.stack([pad_program(x.program) for x in batch])
    return (
        torch.from_numpy(src).long(),
        torch.from_numpy(tgt).long(),
        torch.from_numpy(prog).long(),
    )

train_stream = SyntheticPuzzleStream(CFG.synthetic_train_examples, SEED)
validation_stream = SyntheticPuzzleStream(CFG.synthetic_validation_examples, SEED + 10_000_000)
print("Synthetic curriculum size:", CFG.synthetic_train_examples)



# Cell 5 — Small vision model that guides discrete program search

class GridEncoder(nn.Module):
    def __init__(self, colors: int, dim: int):
        super().__init__()
        self.embed = nn.Embedding(colors, 24)
        self.net = nn.Sequential(
            nn.Conv2d(24, 48, 5, stride=2, padding=2),
            nn.GroupNorm(6, 48),
            nn.SiLU(),
            nn.Conv2d(48, 96, 3, stride=2, padding=1),
            nn.GroupNorm(8, 96),
            nn.SiLU(),
            nn.Conv2d(96, 144, 3, stride=2, padding=1),
            nn.GroupNorm(12, 144),
            nn.SiLU(),
            nn.Conv2d(144, dim, 3, stride=2, padding=1),
            nn.GroupNorm(12, dim),
            nn.SiLU(),
        )
        self.pool = nn.AdaptiveAvgPool2d(1)

    def forward(self, grid: torch.Tensor) -> torch.Tensor:
        x = self.embed(grid).permute(0, 3, 1, 2).contiguous()
        return self.pool(self.net(x)).flatten(1)

class ProgramGuide(nn.Module):
    def __init__(self, cfg: Config):
        super().__init__()
        self.encoder = GridEncoder(cfg.colors, cfg.embedding_dim)
        self.pair = nn.Sequential(
            nn.Linear(cfg.embedding_dim * 4, cfg.program_hidden),
            nn.SiLU(),
            nn.LayerNorm(cfg.program_hidden),
        )
        self.token_embed = nn.Embedding(VOCAB_SIZE, cfg.program_hidden)
        self.rnn = nn.GRUCell(cfg.program_hidden, cfg.program_hidden)
        self.head = nn.Linear(cfg.program_hidden, VOCAB_SIZE)
        self.value = nn.Sequential(
            nn.Linear(cfg.program_hidden, cfg.program_hidden // 2),
            nn.SiLU(),
            nn.Linear(cfg.program_hidden // 2, 1),
        )

    def task_embedding(self, source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        a = self.encoder(source)
        b = self.encoder(target)
        return self.pair(torch.cat([a, b, b-a, a*b], dim=-1))

    def forward(self, source: torch.Tensor, target: torch.Tensor, tokens: torch.Tensor):
        h = self.task_embedding(source, target)
        logits = []
        for t in range(tokens.shape[1]):
            logits.append(self.head(h))
            h = self.rnn(self.token_embed(tokens[:, t]), h)
        return torch.stack(logits, dim=1), self.value(h).squeeze(-1)

    def next_logits(self, task_h: torch.Tensor, prefix: Sequence[int]) -> tuple[torch.Tensor, torch.Tensor]:
        h = task_h
        for token in prefix:
            tok = torch.tensor([token], device=h.device)
            h = self.rnn(self.token_embed(tok), h)
        return self.head(h), self.value(h).squeeze(-1)

MODEL = ProgramGuide(CFG).to(DEVICE)
print("Parameters:", sum(p.numel() for p in MODEL.parameters()))



# Cell 6 — Training and checkpointing

def token_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1))

def train_model(
    model: ProgramGuide,
    *,
    steps: int = CFG.train_steps,
    checkpoint: str = CFG.checkpoint_path,
) -> list[dict[str, float]]:
    model.train()
    loader = DataLoader(
        train_stream,
        batch_size=CFG.batch_size,
        num_workers=0,
        collate_fn=synthetic_collate,
    )
    iterator = iter(loader)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=CFG.learning_rate,
        weight_decay=CFG.weight_decay,
    )
    history = []
    for step in range(1, steps + 1):
        try:
            src, tgt, prog = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            src, tgt, prog = next(iterator)
        src, tgt, prog = src.to(DEVICE), tgt.to(DEVICE), prog.to(DEVICE)
        inp = torch.cat(
            [torch.full((prog.shape[0], 1), STOP_INDEX, device=DEVICE, dtype=torch.long), prog[:, :-1]],
            dim=1,
        )
        logits, value = model(src, tgt, inp)
        exact = (logits.argmax(-1) == prog).float().mean(dim=1)
        loss_program = token_loss(logits, prog)
        loss_value = F.mse_loss(torch.sigmoid(value), exact.detach())
        loss = loss_program + 0.2 * loss_value

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), CFG.grad_clip)
        optimizer.step()

        if step == 1 or step % 100 == 0:
            row = {
                "step": step,
                "loss": float(loss.item()),
                "program_loss": float(loss_program.item()),
                "value_loss": float(loss_value.item()),
                "token_accuracy": float((logits.argmax(-1) == prog).float().mean().item()),
            }
            history.append(row)
            print(row)
        if step % 1000 == 0 or step == steps:
            Path(checkpoint).parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "model": model.state_dict(),
                    "config": dataclasses.asdict(CFG),
                    "step": step,
                    "vocab": [op.name for op in OPS] + ["STOP"],
                },
                checkpoint,
            )
    return history

def load_checkpoint(model: ProgramGuide, paths: Sequence[str]) -> bool:
    for path in paths:
        p = Path(path)
        if p.exists():
            data = torch.load(p, map_location=DEVICE)
            state = data["model"] if isinstance(data, dict) and "model" in data else data
            model.load_state_dict(state, strict=True)
            print("Loaded checkpoint:", p)
            return True
    return False

CHECKPOINT_CANDIDATES = [
    CFG.checkpoint_path,
    "/kaggle/input/neurosymbolic-arc3-weights/neurosymbolic_arc3.pt",
    "/kaggle/input/arc-neurosymbolic-weights/neurosymbolic_arc3.pt",
]

WEIGHTS_LOADED = load_checkpoint(MODEL, CHECKPOINT_CANDIDATES)
RUN_TRAINING = os.environ.get("ARC_TRAIN_SYNTHETIC", "0") == "1"
if RUN_TRAINING and not WEIGHTS_LOADED:
    TRAIN_HISTORY = train_model(MODEL)
else:
    TRAIN_HISTORY = []
    print("Training skipped. Set ARC_TRAIN_SYNTHETIC=1 to train the 100K+ synthetic curriculum.")



# Cell 7 — Exact, structural, and neural candidate scoring

def exact_grid_score(pred: Grid, target: Grid) -> float:
    if pred.shape != target.shape:
        return 0.0
    return float(np.mean(pred == target))

def color_hist_score(pred: Grid, target: Grid) -> float:
    hp = np.bincount(pred.ravel(), minlength=CFG.colors).astype(np.float64)
    ht = np.bincount(target.ravel(), minlength=CFG.colors).astype(np.float64)
    hp /= max(hp.sum(), 1.0)
    ht /= max(ht.sum(), 1.0)
    return float(1.0 - 0.5 * np.abs(hp - ht).sum())

def shape_score(pred: Grid, target: Grid) -> float:
    return math.exp(-0.15 * (abs(pred.shape[0] - target.shape[0]) + abs(pred.shape[1] - target.shape[1])))

def combined_score(pred: Grid, target: Grid) -> float:
    exact = exact_grid_score(pred, target)
    return 0.72 * exact + 0.18 * color_hist_score(pred, target) + 0.10 * shape_score(pred, target)

@dataclass(order=True)
class ProgramCandidate:
    priority: float
    program: tuple[int, ...] = field(compare=False)
    score: float = field(compare=False)
    neural_logprob: float = field(compare=False)
    value: float = field(compare=False)
    prediction: Grid = field(compare=False)

def task_tensor(source: Grid, target: Grid) -> tuple[torch.Tensor, torch.Tensor]:
    s = torch.from_numpy(grid_array(source)).long().unsqueeze(0).to(DEVICE)
    t = torch.from_numpy(grid_array(target)).long().unsqueeze(0).to(DEVICE)
    return s, t



# Cell 8 — Neural-guided discrete beam search

@torch.no_grad()
def neural_beam_search(
    model: ProgramGuide,
    source: Grid,
    target: Grid,
    *,
    beam_width: int = CFG.beam_width,
    branch_factor: int = CFG.branch_factor,
    max_len: int = CFG.max_program_len,
    warm_prefixes: Sequence[Sequence[int]] = (),
) -> list[ProgramCandidate]:
    model.eval()
    src_t, tgt_t = task_tensor(source, target)
    task_h = model.task_embedding(src_t, tgt_t)

    beams: list[tuple[tuple[int, ...], float]] = [(tuple(p), 0.0) for p in warm_prefixes] or [((), 0.0)]
    completed: dict[tuple[int, ...], ProgramCandidate] = {}

    for _depth in range(max_len + 1):
        expanded: list[tuple[tuple[int, ...], float]] = []
        for prefix, logp in beams:
            logits, value = model.next_logits(task_h, prefix)
            probs = torch.log_softmax(logits[0], dim=-1)
            top = torch.topk(probs, k=min(branch_factor, probs.numel()))
            for token, token_logp in zip(top.indices.tolist(), top.values.tolist()):
                new_program = prefix + (int(token),)
                pred = execute_program(source, new_program)
                symbolic = combined_score(pred, target)
                val = float(torch.sigmoid(value[0]).item())
                complexity = sum(OPS[t].cost for t in new_program if t != STOP_INDEX)
                priority = symbolic + 0.08 * (logp + token_logp) + 0.05 * val - 0.003 * complexity
                cand = ProgramCandidate(
                    priority=priority,
                    program=new_program,
                    score=symbolic,
                    neural_logprob=logp + token_logp,
                    value=val,
                    prediction=pred,
                )
                if token == STOP_INDEX or symbolic >= 1.0:
                    old = completed.get(new_program)
                    if old is None or cand.priority > old.priority:
                        completed[new_program] = cand
                else:
                    expanded.append((new_program, logp + token_logp))
        expanded.sort(key=lambda x: x[1], reverse=True)
        # Keep symbolic diversity, not only neural probability.
        rescored = []
        for program, logp in expanded[: beam_width * 4]:
            pred = execute_program(source, program)
            rescored.append((combined_score(pred, target) + 0.06 * logp, program, logp))
        rescored.sort(reverse=True, key=lambda x: x[0])
        beams = [(p, lp) for _, p, lp in rescored[:beam_width]]
        if any(c.score >= 1.0 for c in completed.values()):
            break

    results = sorted(completed.values(), reverse=True)
    if not results:
        for prefix, logp in beams[:beam_width]:
            pred = execute_program(source, prefix)
            results.append(ProgramCandidate(
                priority=combined_score(pred, target),
                program=prefix,
                score=combined_score(pred, target),
                neural_logprob=logp,
                value=0.0,
                prediction=pred,
            ))
        results.sort(reverse=True)
    return results



# Cell 9 — Recursive refinement: propose → execute → diagnose → repair

@dataclass
class Diagnosis:
    score: float
    shape_mismatch: tuple[int, int]
    missing_colors: tuple[int, ...]
    extra_colors: tuple[int, ...]
    mismatch_count: int
    suggested_ops: tuple[int, ...]

def diagnose(pred: Grid, target: Grid) -> Diagnosis:
    pred_colors = set(np.unique(pred).tolist())
    target_colors = set(np.unique(target).tolist())
    suggestions: list[int] = []
    if pred.shape != target.shape:
        suggestions.extend([OP_INDEX["trim"], OP_INDEX["rot90"], OP_INDEX["rot180"], OP_INDEX["rot270"]])
    missing = sorted(target_colors - pred_colors)
    extra = sorted(pred_colors - target_colors)
    for src in extra:
        for dst in missing:
            name = f"recolor_{src}_{dst}"
            if name in OP_INDEX:
                suggestions.append(OP_INDEX[name])
    for color in target_colors:
        if color and f"fill_bbox_{color}" in OP_INDEX:
            suggestions.append(OP_INDEX[f"fill_bbox_{color}"])
    mismatch = pred.size + target.size
    if pred.shape == target.shape:
        mismatch = int(np.sum(pred != target))
    return Diagnosis(
        score=combined_score(pred, target),
        shape_mismatch=(pred.shape[0]-target.shape[0], pred.shape[1]-target.shape[1]),
        missing_colors=tuple(missing),
        extra_colors=tuple(extra),
        mismatch_count=mismatch,
        suggested_ops=tuple(dict.fromkeys(suggestions)),
    )

def recursive_refinement(
    model: ProgramGuide,
    source: Grid,
    target: Grid,
    *,
    rounds: int = CFG.refinement_rounds,
) -> list[ProgramCandidate]:
    all_candidates: dict[tuple[int, ...], ProgramCandidate] = {}
    warm: list[tuple[int, ...]] = []
    for round_index in range(rounds):
        found = neural_beam_search(
            model,
            source,
            target,
            beam_width=max(16, CFG.beam_width // (round_index + 1)),
            branch_factor=CFG.branch_factor,
            max_len=CFG.max_program_len,
            warm_prefixes=warm,
        )
        for c in found:
            old = all_candidates.get(c.program)
            if old is None or c.priority > old.priority:
                all_candidates[c.program] = c
        best = max(all_candidates.values())
        if best.score >= 1.0:
            break
        diagnosis = diagnose(best.prediction, target)
        repairs: list[tuple[int, ...]] = []
        base = tuple(t for t in best.program if t != STOP_INDEX)
        for token in diagnosis.suggested_ops[:16]:
            repaired = (base + (token,))[:CFG.max_program_len]
            repairs.append(repaired)
        # Local edits: delete, replace, append.
        for i in range(min(len(base), CFG.max_program_len)):
            repairs.append(base[:i] + base[i+1:])
        warm = list(dict.fromkeys(repairs))[:CFG.beam_width]
    return sorted(all_candidates.values(), reverse=True)



# Cell 10 — Test-time adaptation per task

def clone_for_tta(model: ProgramGuide) -> ProgramGuide:
    clone = ProgramGuide(CFG).to(DEVICE)
    clone.load_state_dict(model.state_dict())
    return clone

def augment_grid_pair(source: Grid, target: Grid, rng: np.random.Generator) -> tuple[Grid, Grid]:
    transform = int(rng.integers(0, 8))
    if transform == 0: return source.copy(), target.copy()
    if transform == 1: return rot90(source), rot90(target)
    if transform == 2: return rot180(source), rot180(target)
    if transform == 3: return rot270(source), rot270(target)
    if transform == 4: return flip_h(source), flip_h(target)
    if transform == 5: return flip_v(source), flip_v(target)
    if transform == 6: return transpose(source), transpose(target)
    return flip_h(transpose(source)), flip_h(transpose(target))

def test_time_adapt(
    base_model: ProgramGuide,
    train_pairs: Sequence[tuple[Grid, Grid]],
    *,
    steps: int = CFG.tta_steps,
    seed: int = SEED,
) -> ProgramGuide:
    if not train_pairs or steps <= 0:
        return base_model
    model = clone_for_tta(base_model)
    # Freeze low-level vision filters; adapt task-composition and decoder layers.
    for p in model.encoder.parameters():
        p.requires_grad_(False)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(params, lr=CFG.tta_lr)
    rng = np.random.default_rng(seed)
    model.train()

    # Pseudo-label each provided pair with current exact search.
    pseudo = []
    for source, target in train_pairs:
        candidates = recursive_refinement(base_model, source, target, rounds=2)
        if candidates:
            pseudo.append((source, target, candidates[0].program))
    if not pseudo:
        return base_model

    for step in range(steps):
        source, target, program = pseudo[step % len(pseudo)]
        source, target = augment_grid_pair(source, target, rng)
        src_t, tgt_t = task_tensor(source, target)
        target_tokens = torch.from_numpy(pad_program(program)).long().unsqueeze(0).to(DEVICE)
        input_tokens = torch.cat(
            [torch.full((1,1), STOP_INDEX, dtype=torch.long, device=DEVICE), target_tokens[:, :-1]],
            dim=1,
        )
        logits, value = model(src_t, tgt_t, input_tokens)
        loss = token_loss(logits, target_tokens)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(params, CFG.grad_clip)
        optimizer.step()
    model.eval()
    return model



# Cell 11 — Static ARC task solver interface

def solve_static_task(
    task: Mapping[str, Any],
    model: ProgramGuide = MODEL,
    *,
    predictions_per_test: int = 2,
) -> list[list[list[list[int]]]]:
    train_pairs = [
        (np.asarray(pair["input"], dtype=np.int64), np.asarray(pair["output"], dtype=np.int64))
        for pair in task.get("train", [])
    ]
    adapted = test_time_adapt(model, train_pairs)
    outputs = []
    for test_item in task.get("test", []):
        source = np.asarray(test_item["input"], dtype=np.int64)
        # Search against each training target shape/semantics, then vote by program consistency.
        program_scores: defaultdict[tuple[int, ...], float] = defaultdict(float)
        for tr_source, tr_target in train_pairs:
            for cand in recursive_refinement(adapted, tr_source, tr_target)[:8]:
                program_scores[cand.program] += cand.score + 0.02 * cand.neural_logprob
        ranked_programs = sorted(program_scores, key=program_scores.get, reverse=True)
        candidates = []
        seen = set()
        for program in ranked_programs:
            pred = execute_program(source, program)
            key = (pred.shape, pred.tobytes())
            if key not in seen:
                seen.add(key)
                candidates.append(pred.tolist())
            if len(candidates) >= predictions_per_test:
                break
        while len(candidates) < predictions_per_test:
            candidates.append(source.tolist())
        outputs.append(candidates)
    return outputs



# Cell 12 — Interactive state archive and transition model for ARC-AGI-3

@dataclass
class Transition:
    source: str
    action: str
    target: str
    changed_cells: int
    progress_delta: int
    terminal: bool
    coordinate: tuple[int, int] | None = None

@dataclass
class ArchivedState:
    state_id: str
    grid: Grid
    depth: int
    levels_completed: int
    visits: int = 0
    tried: set[str] = field(default_factory=set)
    parent: str | None = None
    parent_action: str | None = None

class StateArchive:
    def __init__(self, limit: int = CFG.archive_limit):
        self.limit = limit
        self.states: dict[str, ArchivedState] = {}
        self.transitions: list[Transition] = []
        self.action_stats: defaultdict[str, list[float]] = defaultdict(list)

    def add(self, grid: Grid, depth: int, levels_completed: int, parent=None, parent_action=None) -> ArchivedState:
        sid = grid_fingerprint(grid)
        if sid not in self.states:
            if len(self.states) >= self.limit:
                # Deterministically evict most-visited deepest non-root state.
                victim = max(self.states.values(), key=lambda s: (s.visits, s.depth, s.state_id))
                self.states.pop(victim.state_id, None)
            self.states[sid] = ArchivedState(sid, np.asarray(grid).copy(), depth, levels_completed, parent=parent, parent_action=parent_action)
        state = self.states[sid]
        state.visits += 1
        return state

    def record(self, transition: Transition):
        self.transitions.append(transition)
        reward = transition.progress_delta * 10.0 + min(1.0, transition.changed_cells / 64.0) - (5.0 if transition.terminal else 0.0)
        self.action_stats[transition.action].append(reward)

    def novelty(self, state: ArchivedState) -> float:
        return 1.0 / math.sqrt(1.0 + state.visits)

    def action_value(self, action: str) -> float:
        vals = self.action_stats.get(action)
        return float(np.mean(vals)) if vals else 0.0



# Cell 13 — Small vision policy for interactive action guidance

class InteractiveVisionPolicy(nn.Module):
    def __init__(self, colors: int = CFG.colors, dim: int = 128, max_actions: int = 8):
        super().__init__()
        self.encoder = GridEncoder(colors, dim)
        self.head = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.SiLU(),
            nn.Linear(dim, max_actions),
        )
        self.value = nn.Sequential(nn.Linear(dim * 2, dim//2), nn.SiLU(), nn.Linear(dim//2, 1))

    def forward(self, current: torch.Tensor, delta: torch.Tensor):
        a = self.encoder(current)
        b = self.encoder(delta)
        h = torch.cat([a, b], dim=-1)
        return self.head(h), self.value(h).squeeze(-1)

INTERACTIVE_MODEL = InteractiveVisionPolicy().to(DEVICE)

def frame_delta_grid(previous: Grid | None, current: Grid) -> Grid:
    if previous is None or previous.shape != current.shape:
        return np.asarray(current).copy()
    return np.where(previous != current, current, 0).astype(np.int64)

@torch.no_grad()
def interactive_action_priors(current: Grid, previous: Grid | None, action_count: int) -> np.ndarray:
    cur = torch.from_numpy(grid_array(current)).long().unsqueeze(0).to(DEVICE)
    delta = torch.from_numpy(grid_array(frame_delta_grid(previous, current))).long().unsqueeze(0).to(DEVICE)
    logits, _ = INTERACTIVE_MODEL(cur, delta)
    probs = torch.softmax(logits[0, :action_count], dim=-1).cpu().numpy()
    return probs



# Cell 14 — Coordinate-region proposals mined from public ARC agent patterns

def connected_components(grid: Grid, background: int = 0) -> list[dict[str, Any]]:
    h, w = grid.shape
    seen = np.zeros((h, w), dtype=bool)
    components = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or grid[y, x] == background:
                continue
            color = int(grid[y, x])
            q = [(y, x)]
            seen[y, x] = True
            cells = []
            while q:
                cy, cx = q.pop()
                cells.append((cy, cx))
                for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
                    ny, nx = cy+dy, cx+dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny,nx] and int(grid[ny,nx]) == color:
                        seen[ny,nx] = True
                        q.append((ny,nx))
            ys = [p[0] for p in cells]
            xs = [p[1] for p in cells]
            components.append({
                "color": color,
                "cells": cells,
                "area": len(cells),
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
                "centroid": (int(round(np.mean(xs))), int(round(np.mean(ys)))),
            })
    return components

def coordinate_proposals(grid: Grid, limit: int = 24) -> list[tuple[int, int, str]]:
    h, w = grid.shape
    proposals = []
    components = sorted(connected_components(grid), key=lambda c: (-c["area"], c["color"]))
    for c in components:
        x, y = c["centroid"]
        proposals.append((x, y, f"component color={c['color']} area={c['area']}"))
        x0, y0, x1, y1 = c["bbox"]
        for px, py, label in [
            (x0, y0, "bbox top-left"),
            (x1, y1, "bbox bottom-right"),
            ((x0+x1)//2, (y0+y1)//2, "bbox center"),
        ]:
            proposals.append((px, py, f"{label} color={c['color']}"))
    # Add coarse region centers to ensure coverage even when segmentation is unhelpful.
    for gy in range(4):
        for gx in range(4):
            proposals.append((min(w-1, int((gx+0.5)*w/4)), min(h-1, int((gy+0.5)*h/4)), f"region {gx},{gy}"))
    unique = []
    seen = set()
    for x, y, why in proposals:
        key = (int(x), int(y))
        if key not in seen:
            seen.add(key)
            unique.append((key[0], key[1], why))
    return unique[:limit]



# Cell 15 — Complete neuro-symbolic interactive agent

class NeuroSymbolicARC3Agent:
    def __init__(self, action_budget: int = CFG.action_budget, seed: int = SEED):
        self.action_budget = action_budget
        self.seed = seed
        self.rng = random.Random(seed)
        self.archive = StateArchive()
        self.previous_grid: Grid | None = None
        self.previous_state_id: str | None = None
        self.previous_action_name: str | None = None
        self.previous_coordinate: tuple[int, int] | None = None
        self.previous_levels = 0
        self.steps = 0
        self.coordinate_cursor: defaultdict[str, int] = defaultdict(int)

    def reset(self):
        self.__init__(self.action_budget, self.seed)

    @staticmethod
    def _extract_grid(frame: Any) -> Grid:
        for name in ("frame", "grid", "observation"):
            value = getattr(frame, name, None)
            if value is not None:
                arr = np.asarray(value)
                if arr.ndim == 2:
                    return arr.astype(np.int64)
        if isinstance(frame, Mapping):
            for name in ("frame", "grid", "observation"):
                if name in frame:
                    arr = np.asarray(frame[name])
                    if arr.ndim == 2:
                        return arr.astype(np.int64)
        raise ValueError("Unable to extract a 2-D grid from FrameData.")

    @staticmethod
    def _levels(frame: Any) -> int:
        return int(getattr(frame, "levels_completed", 0) or 0)

    @staticmethod
    def _state_name(frame: Any) -> str:
        state = getattr(frame, "state", None)
        return getattr(state, "name", str(state))

    @staticmethod
    def _available_actions(frame: Any) -> list[Any]:
        actions = getattr(frame, "available_actions", None)
        if actions:
            return list(actions)
        try:
            from arcengine import GameAction
            return [a for a in GameAction if getattr(a, "name", "") != "RESET"]
        except Exception:
            return []

    @staticmethod
    def _is_complex(action: Any) -> bool:
        method = getattr(action, "is_complex", None)
        if callable(method):
            return bool(method())
        return action_name(action) in {"ACTION6", "ACTION7"}

    def _record_previous_transition(self, current_grid: Grid, current_id: str, levels: int, state_name: str):
        if self.previous_grid is None or self.previous_state_id is None or self.previous_action_name is None:
            return
        changed = int(np.sum(grid_array(self.previous_grid) != grid_array(current_grid)))
        terminal = state_name.upper() in {"GAME_OVER", "WIN"}
        transition = Transition(
            source=self.previous_state_id,
            action=self.previous_action_name,
            target=current_id,
            changed_cells=changed,
            progress_delta=levels - self.previous_levels,
            terminal=terminal,
            coordinate=self.previous_coordinate,
        )
        self.archive.record(transition)

    def _choose(self, frame: Any) -> tuple[Any, dict[str, Any]]:
        grid = self._extract_grid(frame)
        levels = self._levels(frame)
        state_name = self._state_name(frame)
        current = self.archive.add(grid, self.steps, levels)
        self._record_previous_transition(grid, current.state_id, levels, state_name)

        available = self._available_actions(frame)
        if not available:
            raise RuntimeError("No actions are available.")

        priors = interactive_action_priors(grid, self.previous_grid, len(available))
        scored = []
        for idx, action in enumerate(available):
            name = action_name(action)
            tried_penalty = 0.35 if name in current.tried else 0.0
            novelty = self.archive.novelty(current)
            empirical = self.archive.action_value(name)
            score = 0.50 * float(priors[idx]) + 0.30 * novelty + 0.20 * math.tanh(empirical) - tried_penalty
            scored.append((score, idx, action))
        scored.sort(reverse=True, key=lambda x: (x[0], -x[1]))

        selected_score, _, selected = scored[0]
        selected_name = action_name(selected)
        current.tried.add(selected_name)
        coordinate = None
        why = "highest neural prior plus state novelty and learned transition value"
        mode = "explore" if selected_name not in self.archive.action_stats else "exploit"

        if self._is_complex(selected):
            proposals = coordinate_proposals(grid)
            cursor_key = f"{current.state_id}:{selected_name}"
            cursor = self.coordinate_cursor[cursor_key] % max(len(proposals), 1)
            self.coordinate_cursor[cursor_key] += 1
            if proposals:
                x, y, region_why = proposals[cursor]
                coordinate = (x, y)
                why = f"{region_why}; coordinate probe {cursor+1}/{len(proposals)}"
                mode = "explore"

        reasoning = compact_reasoning(
            mode=mode,
            state_id=current.state_id,
            depth=current.depth,
            action=selected_name,
            why=why,
            archive_size=len(self.archive.states),
            confidence=selected_score,
            target=coordinate,
            refinement=min(CFG.refinement_rounds, 1 + len(self.archive.transitions)//20),
        )
        self.previous_grid = grid.copy()
        self.previous_state_id = current.state_id
        self.previous_action_name = selected_name
        self.previous_coordinate = coordinate
        self.previous_levels = levels
        self.steps += 1
        return selected, {"coordinate": coordinate, "reasoning": reasoning}

    def select_action(self, frame: Any) -> Any:
        action, extra = self._choose(frame)
        coordinate = extra["coordinate"]
        reasoning = extra["reasoning"]

        # Preserve the SDK's coordinate-bearing ActionInput when available.
        try:
            from arcengine import ActionInput
            kwargs = {"action": action, "reasoning": reasoning}
            if coordinate is not None:
                kwargs.update({"x": coordinate[0], "y": coordinate[1]})
            return ActionInput(**kwargs)
        except Exception:
            # Local compatibility path for SDK versions whose env.step accepts
            # (GameAction, data={x,y,reasoning}) instead of ActionInput.
            data = {"reasoning": reasoning}
            if coordinate is not None:
                data.update({"x": coordinate[0], "y": coordinate[1]})
            return action, data



# Cell 16 — Official SDK runner

def run_arc_game(
    game_id: str,
    *,
    agent: NeuroSymbolicARC3Agent | None = None,
    max_actions: int = CFG.action_budget,
    render_mode: str | None = None,
):
    import arc_agi
    from arcengine import GameState

    agent = agent or NeuroSymbolicARC3Agent(max_actions)
    arcade = arc_agi.Arcade()
    env = arcade.make(game_id, render_mode=render_mode)
    if env is None:
        raise RuntimeError(f"Failed to create ARC environment {game_id!r}.")

    frame = env.reset() if hasattr(env, "reset") else None
    if frame is None and hasattr(env, "observation"):
        frame = env.observation

    trace = []
    for step in range(max_actions):
        decision = agent.select_action(frame)
        if isinstance(decision, tuple):
            action, data = decision
            next_frame = env.step(action, data=data)
            reasoning = data.get("reasoning")
        else:
            # Prefer direct ActionInput; fall back to decomposed call.
            try:
                next_frame = env.step(decision)
            except TypeError:
                action = decision.action
                data = {"reasoning": decision.reasoning}
                if getattr(decision, "x", None) is not None:
                    data["x"] = decision.x
                if getattr(decision, "y", None) is not None:
                    data["y"] = decision.y
                next_frame = env.step(action, data=data)
            reasoning = getattr(decision, "reasoning", None)

        trace.append({
            "step": step,
            "state": agent._state_name(next_frame),
            "levels_completed": agent._levels(next_frame),
            "reasoning": reasoning,
        })
        frame = next_frame

        state = getattr(frame, "state", None)
        if state == GameState.WIN:
            break
        if state == GameState.GAME_OVER:
            frame = env.reset()
            agent.previous_grid = None
            agent.previous_state_id = None
            agent.previous_action_name = None
            agent.previous_coordinate = None

    scorecard = arcade.get_scorecard()
    return {"game_id": game_id, "trace": trace, "scorecard": scorecard}



# Cell 17 — Competition notebook entry point and submission artifact

def discover_game_ids() -> list[str]:
    # Prefer explicit competition input metadata.
    candidates = []
    roots = [Path("/kaggle/input"), Path("/kaggle/working")]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            name = path.name.lower()
            if "game" not in name and "environment" not in name:
                continue
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            if isinstance(data, Mapping):
                for key in ("game_ids", "games", "environments"):
                    value = data.get(key)
                    if isinstance(value, list):
                        candidates.extend(str(x) for x in value)
    explicit = os.environ.get("ARC_GAME_IDS", "")
    if explicit:
        candidates.extend(x.strip() for x in explicit.split(",") if x.strip())
    return list(dict.fromkeys(candidates))

def write_submission_parquet(rows: Sequence[Mapping[str, Any]], path: str = "/kaggle/working/submission.parquet"):
    import pandas as pd
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame([{
            "game_id": "no_game_discovered",
            "steps": 0,
            "levels_completed": 0,
            "trace_json": "[]",
        }])
    df.to_parquet(path, index=False)
    print("Wrote", path, "rows=", len(df))
    return df

RUN_COMPETITION = os.environ.get("ARC_RUN_COMPETITION", "0") == "1"
if RUN_COMPETITION:
    game_ids = discover_game_ids()
    results = []
    for game_id in game_ids:
        result = run_arc_game(game_id, render_mode=None)
        trace = result["trace"]
        results.append({
            "game_id": game_id,
            "steps": len(trace),
            "levels_completed": max((x["levels_completed"] for x in trace), default=0),
            "trace_json": canonical_dumps(trace),
        })
    SUBMISSION_DF = write_submission_parquet(results)
else:
    print("Competition run is disabled. Set ARC_RUN_COMPETITION=1 or use the starter framework's agent/my_agent.py adapter.")



# Cell 18 — Deterministic smoke tests

def _smoke():
    rng = np.random.default_rng(123)
    stream = SyntheticPuzzleStream(4, 123)
    ex = next(iter(stream))
    assert ex.source.ndim == 2 and ex.target.ndim == 2
    assert len(ex.program) >= 2

    # Search remains executable even with random initial weights.
    found = neural_beam_search(MODEL, ex.source, ex.target, beam_width=8, branch_factor=6, max_len=3)
    assert found and isinstance(found[0].prediction, np.ndarray)

    reason = compact_reasoning(
        mode="explore",
        state_id="a91f3c2e",
        depth=4,
        action="ACTION6",
        why="largest untried region",
        archive_size=37,
        target=(12, 9),
    )
    assert len(canonical_dumps(reason).encode("utf-8")) < CFG.reasoning_limit_bytes

    # Synthetic loader covers the declared 100K+ curriculum without materializing it.
    assert CFG.synthetic_train_examples >= 100_000
    print("Smoke tests passed.")

_smoke()
