#!/usr/bin/env python3

def extract(path):
    with open(path, "r", encoding="utf-8") as f:
        return set([c for c in f.read() if not c.isspace()])

visible = extract("~/phi111/canon_visible_111.idx".replace("~", "/data/data/com.termux/files/home"))
vocab   = extract("~/phi111/canon_vocab_111.idx".replace("~", "/data/data/com.termux/files/home"))

missing = visible - vocab

print("Missing glyphs from vocab:")
for g in missing:
    print(g)
