# SigilAGI Deterministic Capsule Pipeline

This repository contains a deterministic Python capsule pipeline for:

- packing a source tree into a single self-rehydrating capsule
- verifying capsule identity and payload integrity
- rehydrating source files to disk
- booting the rehydrated stack
- asserting deterministic output
- comparing source and rehydrated file hashes

## Current slice

- proxy_pointer_rag.py
- system_refiner.py
- discount_combiner.py
- enhancement_discovery.py
- sigil_stack.py

## Core commands

Run the full pipeline:

```bash
bash ~/collapse/run_pipeline.sh
python3 ~/sigilagi_real_capsule.py --verify-only
python3 ~/collapse/compare_rehydrated_hashes.py --source ~/sigilagi_real --rehydrated ~/sigilagi_real_out
