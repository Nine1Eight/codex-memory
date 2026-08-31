# CPCR-GIT Residual Adapter Builder v1

Local Linux builder/test harness for the Nemotron LoRA-adapter path.

## Hard requirements

- Linux
- Python 3.10+
- `torch`
- `safetensors`
- `pytest` for tests

No fallback adapter path is used. Missing `torch` or `safetensors` is a hard failure.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run full local test pipeline

```bash
./run_local_tests.sh
```

This verifies:

- answer normalization
- CPCR stage routing
- verified solver rows
- GlyphMatics byte/Braille roundtrip
- residual row creation
- real `adapter_model.safetensors` write/read
- rank `<=32` enforcement
- zero-tensor rejection
- nested zip rejection
- root-level `submission.zip` packaging

## CLI

Generate seed direct-answer corpus:

```bash
python -m cpcr_git_builder.cli generate-seed-corpus \
  --out-jsonl build/seed_train.jsonl \
  --report build/seed_report.json
```

Build residual corpus from CSV with `prompt`, `question`, `input`, or `problem` column:

```bash
python -m cpcr_git_builder.cli build-residual-corpus \
  --prompts-csv prompts.csv \
  --out-jsonl build/residual_train.jsonl \
  --report build/residual_report.json \
  --include-quarantine-verified
```

Create a real local test adapter fixture:

```bash
python -m cpcr_git_builder.cli write-test-adapter \
  --adapter-dir build/test_adapter \
  --rank 8 \
  --hidden 64
```

Validate a competition adapter:

```bash
python -m cpcr_git_builder.cli validate-adapter \
  --adapter-dir /path/to/adapter \
  --max-rank 32
```

Package a flat root-level submission zip:

```bash
python -m cpcr_git_builder.cli package-adapter \
  --adapter-dir /path/to/adapter \
  --out-zip /kaggle/working/submission.zip \
  --max-rank 32
```

Validate the final zip:

```bash
python -m cpcr_git_builder.cli validate-submission \
  --zip /kaggle/working/submission.zip \
  --max-rank 32
```

## Architecture

```text
raw prompts / train rows
  ↓
category inference
  ↓
CPCR routing
  ├─ stage 0 anchors: cipher, numeral, unit, gravity
  ├─ stage 1 symbolic/numeric expansion
  ├─ stage 2 cryptarithm verified repair
  └─ stage 3 quarantine verified-only bit manipulation
  ↓
GIT direct boxed-answer rows
  ↓
residual solver repair ledger
  ↓
train JSONL
  ↓
rank<=32 LoRA adapter
  ↓
safetensors validation
  ↓
flat submission.zip
```

## Competition guardrails

- Adapter rank must be `<=32`.
- `adapter_model.safetensors` must contain non-zero LoRA tensors.
- Submission zip must contain root-level files only:
  - `adapter_config.json`
  - `adapter_model.safetensors`
- Dummy/tiny/zero adapters fail validation.
- Nested zip paths fail validation.
