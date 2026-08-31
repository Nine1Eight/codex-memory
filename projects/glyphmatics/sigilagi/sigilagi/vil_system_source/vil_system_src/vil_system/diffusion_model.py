"""
Stub interface for diffusion‑style generative models in the VIL system.

In the Visual Instruction Learning architecture, a diffusion model is
conditioned on a latent control vector derived from visual instructions
to produce deterministic outputs with stable identities and motion
patterns【527482634550503†L0-L15】.  This module defines a `DiffusionModel` class
that encapsulates this interface.  The current implementation is a
placeholder: it generates a blank image or random noise depending on
the `mode` parameter.  To integrate a real diffusion model, subclass
`DiffusionModel` and override the `generate` method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from PIL import Image


@dataclass
class DiffusionModel:
    """Base class for diffusion‑style generative models."""

    image_size: int = 256
    mode: str = "noise"  # or 'blank'

    def generate(self, latent_control: np.ndarray, seed: Optional[int] = None) -> Image.Image:
        """
        Generate an image conditioned on a latent control vector.

        Parameters
        ----------
        latent_control : numpy.ndarray
            The latent control vector produced by `LatentControlEncoder`.
        seed : int, optional
            Random seed for reproducibility.

        Returns
        -------
        PIL.Image.Image
            The generated image.  In the base implementation this is either
            white noise or a blank canvas.
        """
        if seed is not None:
            np.random.seed(seed)
        # Determine output mode
        if self.mode == "blank":
            arr = np.ones((self.image_size, self.image_size, 3), dtype=np.uint8) * 255
        else:
            # White noise modulated by latent control vector
            noise = np.random.rand(self.image_size, self.image_size, 3)
            # Use the mean of the latent control vector to modulate noise intensity
            intensity = float(np.mean(latent_control)) if latent_control.size > 0 else 0.5
            arr = np.clip(noise * 255 * intensity, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode="RGB")