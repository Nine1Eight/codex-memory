from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from safetensors.torch import load_file, save_file

@dataclass
class AdapterValidation:
    ok: bool
    adapter_dir: str
    rank: int
    tensor_count: int
    total_elements: int
    total_abs_sum: float
    has_lora_a: bool
    has_lora_b: bool
    errors: List[str]
    warnings: List[str]

    def assert_ok(self) -> None:
        if not self.ok:
            raise AssertionError("adapter validation failed: " + "; ".join(self.errors))


def _read_config(adapter_dir: Path) -> dict:
    cfg_path = adapter_dir / "adapter_config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"missing {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def adapter_rank(config: dict) -> int:
    r = config.get("r", config.get("rank", None))
    if r is None:
        raise ValueError("adapter_config.json missing LoRA rank field `r`")
    return int(r)


def validate_adapter_dir(adapter_dir: str | Path, max_rank: int = 32, min_total_elements: int = 128) -> AdapterValidation:
    adapter_dir = Path(adapter_dir)
    errors: List[str] = []
    warnings: List[str] = []
    rank = -1
    tensor_count = 0
    total_elements = 0
    total_abs_sum = 0.0
    has_lora_a = False
    has_lora_b = False

    cfg_path = adapter_dir / "adapter_config.json"
    st_path = adapter_dir / "adapter_model.safetensors"
    if not cfg_path.exists():
        errors.append("missing adapter_config.json")
    if not st_path.exists():
        errors.append("missing adapter_model.safetensors")
    if errors:
        return AdapterValidation(False, str(adapter_dir), rank, tensor_count, total_elements, total_abs_sum, has_lora_a, has_lora_b, errors, warnings)

    try:
        cfg = _read_config(adapter_dir)
        rank = adapter_rank(cfg)
        if rank <= 0:
            errors.append(f"invalid rank {rank}; must be positive")
        if rank > max_rank:
            errors.append(f"rank {rank} exceeds max_rank {max_rank}")
        if str(cfg.get("peft_type", "")).upper() != "LORA":
            warnings.append("peft_type is not LORA")
    except Exception as e:
        errors.append(f"invalid adapter_config.json: {e}")

    try:
        tensors = load_file(str(st_path), device="cpu")
        tensor_count = len(tensors)
        if tensor_count == 0:
            errors.append("safetensors file contains zero tensors")
        for name, tensor in tensors.items():
            total_elements += int(tensor.numel())
            total_abs_sum += float(tensor.detach().abs().sum().item())
            lname = name.lower()
            has_lora_a = has_lora_a or "lora_a" in lname
            has_lora_b = has_lora_b or "lora_b" in lname
            if rank > 0 and "lora_a" in lname and tensor.ndim >= 2 and rank not in tensor.shape:
                warnings.append(f"{name} does not expose rank dimension {rank}: shape={tuple(tensor.shape)}")
            if rank > 0 and "lora_b" in lname and tensor.ndim >= 2 and rank not in tensor.shape:
                warnings.append(f"{name} does not expose rank dimension {rank}: shape={tuple(tensor.shape)}")
        if total_elements < min_total_elements:
            errors.append(f"too few tensor elements: {total_elements} < {min_total_elements}")
        if total_abs_sum <= 0:
            errors.append("all adapter tensors are zero")
        if not has_lora_a:
            errors.append("no LoRA A tensor found")
        if not has_lora_b:
            errors.append("no LoRA B tensor found")
    except Exception as e:
        errors.append(f"invalid adapter_model.safetensors: {e}")

    return AdapterValidation(len(errors) == 0, str(adapter_dir), rank, tensor_count, total_elements, total_abs_sum, has_lora_a, has_lora_b, errors, warnings)


def write_test_adapter(adapter_dir: str | Path, rank: int = 8, hidden: int = 64, seed: int = 918) -> Path:
    """Create a real non-empty LoRA adapter for local contract tests.

    This is not a competition adapter; it is a safetensors/rank/package contract
    fixture that catches dummy, nested, rank>32, and zero-tensor failures.
    """
    adapter_dir = Path(adapter_dir)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    if rank <= 0:
        raise ValueError("rank must be positive")
    g = torch.Generator(device="cpu").manual_seed(seed)
    cfg = {
        "base_model_name_or_path": "nvidia/Nemotron-3-Nano-30B-A3B",
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "init_lora_weights": True,
        "lora_alpha": rank * 2,
        "lora_dropout": 0.0,
        "modules_to_save": None,
        "peft_type": "LORA",
        "r": rank,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
        "task_type": "CAUSAL_LM",
    }
    (adapter_dir / "adapter_config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
    tensors = {}
    for layer in range(2):
        for proj in ["q_proj", "k_proj", "v_proj", "o_proj"]:
            prefix = f"base_model.model.model.layers.{layer}.self_attn.{proj}"
            tensors[f"{prefix}.lora_A.weight"] = torch.randn(rank, hidden, generator=g, dtype=torch.float32) * 0.01
            tensors[f"{prefix}.lora_B.weight"] = torch.randn(hidden, rank, generator=g, dtype=torch.float32) * 0.01
    save_file(tensors, str(adapter_dir / "adapter_model.safetensors"))
    return adapter_dir


def package_adapter_zip(adapter_dir: str | Path, out_zip: str | Path, max_rank: int = 32) -> AdapterValidation:
    adapter_dir = Path(adapter_dir)
    out_zip = Path(out_zip)
    validation = validate_adapter_dir(adapter_dir, max_rank=max_rank)
    validation.assert_ok()
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in ["adapter_config.json", "adapter_model.safetensors"]:
            zf.write(adapter_dir / name, arcname=name)
    return validation


def validate_submission_zip(zip_path: str | Path, max_rank: int = 32) -> AdapterValidation:
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    extract_dir = zip_path.parent / (zip_path.stem + "_extract_check")
    if extract_dir.exists():
        for child in extract_dir.iterdir():
            if child.is_file():
                child.unlink()
            else:
                raise RuntimeError(f"refusing to clean nested dir {child}")
    else:
        extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        nested = [n for n in names if "/" in n.strip("/")]
        if nested:
            raise AssertionError(f"submission zip must be flat/root-level; nested entries={nested[:5]}")
        required = {"adapter_config.json", "adapter_model.safetensors"}
        missing = required - set(names)
        if missing:
            raise AssertionError(f"submission zip missing {sorted(missing)}")
        zf.extractall(extract_dir)
    return validate_adapter_dir(extract_dir, max_rank=max_rank)


def validation_report(validation: AdapterValidation) -> str:
    return json.dumps(asdict(validation), indent=2, sort_keys=True)
