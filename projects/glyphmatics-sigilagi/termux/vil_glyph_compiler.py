#!/usr/bin/env python3
import hashlib

CANON_SIZE = 111
START_111 = 109
STOP_111 = 110

def compile_base111(text, max_len=128):
    out = [START_111]
    data = text.encode("utf-8")

    for i, b in enumerate(data[:max_len-2]):
        h = hashlib.sha256(bytes([b]) + i.to_bytes(2, "little")).digest()
        out.append(int(h[0]) % CANON_SIZE)

    out.append(STOP_111)
    return out

def base111_to_glyph_tokens(indices):
    tokens = []
    for i, x in enumerate(indices):
        if x == START_111:
            tokens.append((15 << 8) | 254)
        elif x == STOP_111:
            tokens.append((15 << 8) | 255)
        else:
            g = x % 16
            b = (x * 37 + i * 17) % 256
            tokens.append((g << 8) | b)
    return tokens
