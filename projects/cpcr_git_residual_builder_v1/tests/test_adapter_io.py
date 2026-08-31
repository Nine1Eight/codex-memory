import json
import zipfile
from pathlib import Path

import pytest
import torch
from safetensors.torch import load_file, save_file

from cpcr_git_builder.adapter_io import (
    package_adapter_zip,
    validate_adapter_dir,
    validate_submission_zip,
    write_test_adapter,
)


def test_real_safetensors_adapter_validate_and_package(tmp_path: Path):
    adapter = write_test_adapter(tmp_path / "adapter", rank=8, hidden=64)
    v = validate_adapter_dir(adapter)
    assert v.ok, v.errors
    assert v.rank == 8
    assert v.tensor_count > 0
    assert v.total_abs_sum > 0
    out_zip = tmp_path / "submission.zip"
    package_adapter_zip(adapter, out_zip)
    assert out_zip.exists()
    with zipfile.ZipFile(out_zip, "r") as zf:
        assert sorted(zf.namelist()) == ["adapter_config.json", "adapter_model.safetensors"]
    vz = validate_submission_zip(out_zip)
    assert vz.ok, vz.errors


def test_rank_over_32_fails(tmp_path: Path):
    adapter = write_test_adapter(tmp_path / "bad_rank", rank=33, hidden=64)
    v = validate_adapter_dir(adapter, max_rank=32)
    assert not v.ok
    assert any("exceeds" in e for e in v.errors)


def test_zero_tensor_fails(tmp_path: Path):
    adapter = tmp_path / "zero"
    adapter.mkdir()
    cfg = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "r": 8,
        "target_modules": ["q_proj"],
    }
    (adapter / "adapter_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    save_file({
        "base_model.model.layers.0.q_proj.lora_A.weight": torch.zeros(8, 64),
        "base_model.model.layers.0.q_proj.lora_B.weight": torch.zeros(64, 8),
    }, str(adapter / "adapter_model.safetensors"))
    v = validate_adapter_dir(adapter)
    assert not v.ok
    assert any("zero" in e for e in v.errors)


def test_nested_zip_fails(tmp_path: Path):
    adapter = write_test_adapter(tmp_path / "adapter", rank=8, hidden=64)
    nested = tmp_path / "nested.zip"
    with zipfile.ZipFile(nested, "w") as zf:
        zf.write(adapter / "adapter_config.json", "adapter/adapter_config.json")
        zf.write(adapter / "adapter_model.safetensors", "adapter/adapter_model.safetensors")
    with pytest.raises(AssertionError):
        validate_submission_zip(nested)
