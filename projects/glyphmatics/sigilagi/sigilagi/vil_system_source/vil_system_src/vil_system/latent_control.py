"""
Latent control encoder for the VIL system.

The latent control encoder converts a visual instruction (a collage
created by the `VisualInstruction` class) into a fixed‑length vector.
This vector can be used to modulate a diffusion‑style generative model
or other downstream components.  The current implementation uses
simple image statistics as a placeholder: it down‑samples the input
image into an 8×8 grid of mean intensities and computes the global
mean and standard deviation, resulting in a 66‑dimensional vector.

Users can replace or extend this behaviour by subclassing
`LatentControlEncoder` and overriding the `encode` method.  For
instance, a convolutional autoencoder could be trained to produce
compact latent representations of the collage images.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Tuple

import numpy as np
from PIL import Image


@dataclass
class LatentControlEncoder:
    """Encodes collage images into latent control vectors."""

    downsample_size: Tuple[int, int] = (8, 8)

    def encode(self, image: Image.Image) -> np.ndarray:
        """
        Encode an image into a latent control vector.

        Parameters
        ----------
        image : PIL.Image.Image
            The collage image produced by `VisualInstruction.build_collage()`.

        Returns
        -------
        numpy.ndarray
            A one‑dimensional array containing the latent control features.
        """
        # Convert to grayscale
        gray = image.convert("L")
        # Resize to the downsample size
        ds_img = gray.resize(self.downsample_size, Image.Resampling.LANCZOS)
        ds_arr = np.asarray(ds_img, dtype=np.float32) / 255.0
        # Flatten intensities
        features = ds_arr.flatten()
        # Compute global statistics
        mean_val = np.mean(ds_arr)
        std_val = np.std(ds_arr)
        # Concatenate
        return np.concatenate([features, [mean_val, std_val]], axis=0)