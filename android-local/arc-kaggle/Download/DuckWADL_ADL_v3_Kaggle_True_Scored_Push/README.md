# DuckWADL ADL v3 Kaggle true-scored push package

Target kernel:
`wethepeople918/duckwadl-adl-v3-causal-frontier-scored-run`

Competition:
`arc-prize-2026-arc-agi-3`

Accelerator:
`NvidiaRtxPro6000`

Attached inputs:
- `jeroencottaar/taaf-kaggle-source-share`
- `driessmit1/arc3-vllm-h100-wheelhouse-v3`
- `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot`

The notebook refuses a true submission if:
- `/kaggle/working/submission.parquet` is missing;
- required columns `row_id`, `game_id`, `end_of_game`, `score` are missing;
- the file is empty;
- the true rerun produced the offline one-row placeholder;
- ADL transition/report/memory artifacts are missing.

Expected extra output:
`/kaggle/working/duckwadl_output_manifest.json`
