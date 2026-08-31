# VIL System Source Code

This repository contains a reference implementation of a **Visual Instruction Learning** (VIL) system.  VIL treats writing systems not as separate languages but as a single ordered glyph canon and drives a diffusion‑style generative model from **visual instructions** rather than text prompts.  The goal of this codebase is to provide a production‑grade, extensible framework for working with the concepts introduced in the accompanying report.

## Features

* **Canonical glyph catalogue** – The `data/glyph_canon_3x111.txt` file lists three blocks of 111 glyphs each.  These blocks combine characters from the Unicode Private Use Area, the Braille Patterns block and the Miscellaneous Symbols/Dingbats blocks【428112575403411†L124-L156】【389342945334137†L148-L162】.  The `dataset` module exposes these glyphs as a structured `pandas` data frame.
* **Visual instruction builder** – Create collage‑style visual instructions from sequences of glyph indices.  These instructions can incorporate repeated glyphs (identity locks), variations and symmetries to encode motion grammars, stylistic priors and latent control constraints.
* **Latent control encoder** – Convert visual instructions into fixed‑length control vectors.  The provided implementation computes simple image statistics as a placeholder; it can be replaced with a learned encoder (e.g., a convolutional autoencoder) for more sophisticated control signals.
* **Diffusion model interface** – A stub class defines the interface for a diffusion‑style generative model.  It can be implemented using any diffusion library (such as [diffusers](https://github.com/huggingface/diffusers)) to produce images conditioned on latent control.
* **Embedding feature engineering** – Implement a seven‑stage feature‑engineering pipeline for large‑language‑model embeddings, including similarity to anchors, clustering, pairwise interactions, dimensionality reduction, normalization, aggregation and synthetic feature generation【527482634550503†L17-L35】.
* **Training hooks** – Skeleton functions demonstrate how to integrate the dataset, visual instructions, latent control and diffusion model into a training loop.  These stubs are ready to be expanded for custom research or production use.

## Getting Started

### Requirements

The following Python packages are required to run the code:

* Python 3.9+
* `numpy`
* `pandas`
* `scikit‑learn`
* `Pillow`

You can install the dependencies using pip:

```bash
pip install numpy pandas scikit-learn pillow
```

Some parts of the system (e.g., the diffusion model) require additional libraries which are not installed by default.  See the comments in `diffusion_model.py` for guidance on integrating a real diffusion model.

### Usage

Here is a simple example showing how to load the glyph dataset, build a visual instruction and encode it into a latent control vector:

```python
from vil_system.dataset import GlyphDataset
from vil_system.visual_instruction import VisualInstruction
from vil_system.latent_control import LatentControlEncoder

# Load the canonical glyph list
dataset = GlyphDataset()
print(dataset.to_dataframe().head())

# Build a visual instruction from three glyph indices
instr = VisualInstruction(glyph_indices=[0, 1, 2], grid_size=(1, 3))
image = instr.build_collage()
image.show()

# Encode the instruction into a latent control vector
encoder = LatentControlEncoder()
control_vec = encoder.encode(image)
print(control_vec)
```

To run the embedding feature‑engineering pipeline on a list of embeddings:

```python
import numpy as np
from vil_system.embedding_pipeline import EmbeddingFeatureEngineer

# Fake embeddings and anchors for demonstration
embeddings = [np.random.rand(768) for _ in range(10)]
anchors = [np.random.rand(768) for _ in range(3)]

engineer = EmbeddingFeatureEngineer(n_clusters=2, n_components=3)
features = engineer.transform(embeddings, anchor_vectors=anchors)
print(features)
```

The `training` module provides high‑level hooks for integrating these components into a training loop.

## File Structure

* `vil_system_src/vil_system/__init__.py` – Top‑level package exports
* `vil_system_src/vil_system/data/glyph_canon_3x111.txt` – Canonical list of 333 glyphs
* `vil_system_src/vil_system/dataset.py` – Dataset loading utilities
* `vil_system_src/vil_system/visual_instruction.py` – Visual instruction builder
* `vil_system_src/vil_system/latent_control.py` – Latent control encoder
* `vil_system_src/vil_system/diffusion_model.py` – Diffusion model interface
* `vil_system_src/vil_system/embedding_pipeline.py` – Embedding feature‑engineering pipeline
* `vil_system_src/vil_system/training.py` – Training loop stubs
* `vil_system_src/vil_system/utils.py` – Utility functions

## License

This reference implementation is released into the public domain for educational and research purposes.  You are free to reuse, modify and distribute it as long as attribution to the original VIL project is maintained.