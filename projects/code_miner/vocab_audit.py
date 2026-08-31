#!/usr/bin/env python3
import sys
from collections import Counter

with open(sys.argv[1], "r", encoding="utf-8") as f:
    raw = f.read()

glyphs = [c for c in raw if not c.isspace()]

print("Total glyphs:", len(glyphs))

counts = Counter(glyphs)
duplicates = [g for g, c in counts.items() if c > 1]

print("Unique glyphs:", len(counts))
print("Duplicates:", duplicates)
