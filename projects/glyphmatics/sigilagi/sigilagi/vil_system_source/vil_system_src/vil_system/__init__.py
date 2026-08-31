"""
Top‑level package for the Visual Instruction Learning (VIL) system.

The VIL system provides tools to work with a canonical glyph catalogue,
build collage‑style visual instructions, encode those instructions into
latent control vectors, interface with diffusion‑style generative models,
and engineer features from large‑language‑model embeddings.  See the
accompanying `README.md` for a high‑level overview and usage examples.

This package is organised into submodules:

* `dataset` – Load and manipulate the canonical glyph dataset.
* `visual_instruction` – Create visual instruction collages from glyph
  sequences.
* `latent_control` – Encode images into latent control vectors.
* `diffusion_model` – Stub interface for diffusion‑style generative models.
* `embedding_pipeline` – Feature engineering pipeline for embeddings.
* `training` – High‑level training loop stubs.
* `utils` – Miscellaneous utility functions.
"""

from .dataset import GlyphDataset, GlyphInfo
from .visual_instruction import VisualInstruction
from .latent_control import LatentControlEncoder
from .diffusion_model import DiffusionModel
from .embedding_pipeline import EmbeddingFeatureEngineer

__all__ = [
    "GlyphDataset",
    "GlyphInfo",
    "VisualInstruction",
    "LatentControlEncoder",
    "DiffusionModel",
    "EmbeddingFeatureEngineer",
]