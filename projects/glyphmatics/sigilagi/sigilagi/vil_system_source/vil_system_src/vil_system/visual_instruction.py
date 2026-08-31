"""
Visual instruction builder for the VIL system.

This module defines the `VisualInstruction` class, which creates
collage‑style images from sequences of glyph indices.  The collages
encode control information via repetition, variation and symmetry,
following the ideas described in the VIL report【527482634550503†L0-L15】.

The current implementation focuses on deterministic construction of
collages: given a list of glyph indices (referring to entries in the
`GlyphDataset`), the `build_collage` method produces a `PIL.Image`
containing those glyphs arranged on a grid.  Optional rotation and
scaling can be applied to introduce controlled variation.

Future versions could incorporate more sophisticated layout grammars,
motion trajectories or blending operations to more closely follow the
specifications of the VIL architecture.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .dataset import GlyphDataset


@dataclass
class VisualInstruction:
    """Represents a visual instruction composed of glyphs."""

    glyph_indices: Sequence[int]
    grid_size: Optional[Tuple[int, int]] = None
    cell_size: int = 80
    font_size: int = 60
    rotation_range: Tuple[float, float] = (-10.0, 10.0)
    rng_seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.grid_size is None:
            # Default to a single row grid
            self.grid_size = (1, len(self.glyph_indices))
        rows, cols = self.grid_size
        if rows * cols < len(self.glyph_indices):
            raise ValueError(
                f"Grid of size {self.grid_size} cannot hold {len(self.glyph_indices)} glyphs"
            )
        if self.rng_seed is not None:
            random.seed(self.rng_seed)

    def build_collage(self, dataset: Optional[GlyphDataset] = None) -> Image.Image:
        """
        Construct a collage image from the glyph indices.

        Parameters
        ----------
        dataset : GlyphDataset, optional
            The dataset used to resolve glyph indices into characters.  If
            omitted, a default dataset will be loaded.

        Returns
        -------
        PIL.Image.Image
            The generated collage image.
        """
        # Ensure dataset is available
        ds = dataset or GlyphDataset()
        # Retrieve the glyph characters for the indices
        glyphs = [ds.to_list()[idx].glyph for idx in self.glyph_indices]
        rows, cols = self.grid_size or (1, len(glyphs))
        # Compute the total image size
        width = cols * self.cell_size
        height = rows * self.cell_size
        image = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", self.font_size)
        except Exception:
            # Fallback to a default bitmap font
            font = ImageFont.load_default()
        # Place each glyph into the grid
        for idx, glyph in enumerate(glyphs):
            r = idx // cols
            c = idx % cols
            # Create a cell canvas
            cell = Image.new("RGBA", (self.cell_size, self.cell_size), color=(255, 255, 255, 0))
            cell_draw = ImageDraw.Draw(cell)
            w, h = cell_draw.textsize(glyph, font=font)
            # Random rotation within range
            angle = random.uniform(*self.rotation_range)
            # Draw glyph centered in the cell
            glyph_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            glyph_draw = ImageDraw.Draw(glyph_img)
            glyph_draw.text((0, 0), glyph, font=font, fill="black")
            # Rotate glyph
            rotated = glyph_img.rotate(angle, expand=True)
            # Compute position to paste rotated glyph into cell
            rw, rh = rotated.size
            px = (self.cell_size - rw) // 2
            py = (self.cell_size - rh) // 2
            cell.paste(rotated, (px, py), rotated)
            # Paste cell into main image
            image.paste(cell.convert("RGB"), (c * self.cell_size, r * self.cell_size))
        return image