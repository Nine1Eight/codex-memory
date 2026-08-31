#!/usr/bin/env python3

import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    glyphs = [c for c in f.read() if not c.isspace()]

codepoints = sorted([ord(g) for g in glyphs])

print("Min:", hex(codepoints[0]))
print("Max:", hex(codepoints[-1]))
print("Count:", len(codepoints))

missing = []

for i in range(codepoints[0], codepoints[-1] + 1):
    if i not in codepoints:
        missing.append(i)

print("Missing codepoints:")
for m in missing:
    print(hex(m))
