"""
Dataset utilities for the Visual Instruction Learning (VIL) system.

This module exposes classes and functions for parsing the canonical
glyph catalogue into structured representations.  The glyph catalogue
is provided as a plain‑text file with three lines of 111 glyphs each.
These lines correspond to Private Use Area symbols, Braille patterns
and various miscellaneous symbols and dingbats【428112575403411†L124-L156】【389342945334137†L148-L162】.

Example:

    >>> from vil_system.dataset import GlyphDataset
    >>> ds = GlyphDataset()
    >>> df = ds.to_dataframe()
    >>> df.head()

The resulting DataFrame contains the following columns:

```
group   – numeric group identifier (0, 1 or 2)
index   – 0‑based index within the group (0–110)
glyph   – the Unicode character itself
code_point – hexadecimal codepoint string (e.g. 'E000')
unicode_name – name assigned by `unicodedata.name`, or 'PRIVATE USE' if undefined
```
"""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

import pandas as pd

try:
    # Python 3.11 adds removeprefix/removesuffix to bytes, but ensure compatibility
    removeprefix = str.removeprefix  # type: ignore[attr-defined]
except AttributeError:
    def removeprefix(s: str, prefix: str) -> str:
        return s[prefix.__len__():] if s.startswith(prefix) else s


@dataclass(frozen=True)
class GlyphInfo:
    """Structured information about a single glyph entry."""

    group: int
    index: int
    glyph: str
    code_point: str
    unicode_name: str

    def __repr__(self) -> str:
        return (f"GlyphInfo(group={self.group}, index={self.index}, "
                f"glyph='{self.glyph}', code_point='{self.code_point}', "
                f"unicode_name='{self.unicode_name}')")


class GlyphDataset:
    """Loader for the canonical glyph catalogue used by the VIL system."""

    def __init__(self, glyph_canon_path: Optional[str] = None) -> None:
        """
        Initialise the dataset loader.

        Parameters
        ----------
        glyph_canon_path : str, optional
            Path to a canonical glyph list.  If omitted, the bundled
            `data/glyph_canon_3x111.txt` file is used.
        """
        if glyph_canon_path is None:
            # Use the packaged data file relative to this module
            here = Path(__file__).resolve().parent
            glyph_canon_path = here / "data" / "glyph_canon_3x111.txt"
        self.glyph_canon_path = Path(glyph_canon_path)
        if not self.glyph_canon_path.is_file():
            raise FileNotFoundError(f"Glyph canon file not found: {self.glyph_canon_path}")
        self._entries: List[GlyphInfo] = []
        self._loaded: bool = False

    def _load(self) -> None:
        if self._loaded:
            return
        with self.glyph_canon_path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) != 3:
            raise ValueError("Glyph canon must contain exactly three nonempty lines")
        entries: List[GlyphInfo] = []
        for group_idx, line in enumerate(lines):
            glyphs = line.split()
            if len(glyphs) != 111:
                raise ValueError(
                    f"Group {group_idx} should contain 111 glyphs, found {len(glyphs)}"
                )
            for i, glyph in enumerate(glyphs):
                codepoint = f"{ord(glyph):04X}"
                try:
                    name = unicodedata.name(glyph)
                except ValueError:
                    # Private Use Area and some symbols lack official names
                    name = "PRIVATE USE"
                entries.append(GlyphInfo(group=group_idx, index=i, glyph=glyph,
                                         code_point=codepoint, unicode_name=name))
        self._entries = entries
        self._loaded = True

    def __iter__(self) -> Iterator[GlyphInfo]:
        """Iterate over glyph entries."""
        self._load()
        return iter(self._entries)

    def to_list(self) -> List[GlyphInfo]:
        """Return the glyph entries as a list."""
        self._load()
        return list(self._entries)

    def to_dataframe(self) -> pd.DataFrame:
        """Return the glyph entries as a pandas DataFrame."""
        self._load()
        data = {
            "group": [e.group for e in self._entries],
            "index": [e.index for e in self._entries],
            "glyph": [e.glyph for e in self._entries],
            "code_point": [e.code_point for e in self._entries],
            "unicode_name": [e.unicode_name for e in self._entries],
        }
        return pd.DataFrame(data)

    def to_csv(self, out_path: str) -> None:
        """Write the glyph dataset to a CSV file."""
        df = self.to_dataframe()
        df.to_csv(out_path, index=False)

    def __len__(self) -> int:
        self._load()
        return len(self._entries)