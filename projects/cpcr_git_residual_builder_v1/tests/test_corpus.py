import json
from pathlib import Path

from cpcr_git_builder.corpus import build_residual_rows, generate_seed_git_rows, write_jsonl


def test_seed_corpus_sorted_and_boxed(tmp_path: Path):
    rows = generate_seed_git_rows()
    assert rows
    assert rows[0]["cpcr_stage"] == 0
    assert all(r["output"].startswith(r"\boxed{") for r in rows)
    out = tmp_path / "train.jsonl"
    stats = write_jsonl(rows, out, allowed_only=True)
    assert out.exists()
    written = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert len(written) == stats.train_allowed
    assert all(x["train_allowed"] for x in written)


def test_residual_rows_include_verified_bit_late():
    prompts = ["Compute 6 << 2", "This is unknown nonsense"]
    rows = build_residual_rows(prompts, include_quarantine_verified=True)
    bit = [r for r in rows if r["category"] == "bit_manipulation"][0]
    unknown = [r for r in rows if r["category"] == "unknown"][0]
    assert bit["verified"] is True and bit["train_allowed"] is True and bit["cpcr_stage"] == 3
    assert unknown["train_allowed"] is False
