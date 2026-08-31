---
license: mit
task_categories:
  - text-generation
  - feature-extraction
  - text-classification
language:
  - en
tags:
  - glyphmatics
  - sigilagi
  - symbolic-ai
  - semantic-compression
  - neuro-symbolic-ai
  - cognitive-architecture
  - agentic-ai
  - mobile-ai
  - text
pretty_name: GlyphMatics Complete Training Dataset
size_categories:
  - 1K<n<10K
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train.jsonl
      - split: validation
        path: data/validation.jsonl
      - split: test
        path: data/test.jsonl
---

# GlyphMatics Complete Training Dataset

Canonical synthetic training data for GlyphMatics / SigilAGI.

## Covers

- glyph encoding
- glyph decoding
- semantic compression
- reconstruction
- Alpha/Beta/Gamma mapping
- SigilAGI routing
- VIL normalization
- GIIBL lattice blocks
- RC3 cube encoding
- Quantum Glyph states
- mobile deployment planning
- safety-aware symbolic transformation

## Dataset Viewer

The public dataset viewer is configured only for:

- data/train.jsonl
- data/validation.jsonl
- data/test.jsonl

Auxiliary files are stored separately:

- auxiliary/ontology.jsonl
- auxiliary/safety.jsonl

## Author

Matthew Blake Ward  
Founder, 918 Technologies  
Creator of GlyphMatics and SigilAGI
