import hashlib
import numpy as np

DIM = 64

HIEROGLYPH_SEMANTICS = {
    '𓀀': (0, 0xAA), '𓁿': (15, 0xFF), '𓂝': (2, 0x33),
    '𓃀': (1, 0x11), '𓄿': (3, 0x44), '𓅓': (4, 0x55),
    '𓆎': (5, 0x66), '𓇋': (6, 0x77), '𓈖': (7, 0x88),
    '𓉐': (8, 0x99), '𓊪': (9, 0xAA), '𓋹': (10, 0xBB),
    '𓌃': (11, 0xCC), '𓍯': (12, 0xDD), '𓎛': (13, 0xEE),
    '𓏏': (14, 0xFF)
}

MAYA_GLYPH_SEMANTICS = {
    '꙰': (0, 0xAA), '꙱': (9, 0x99), '꙲': (11, 0xCC),
    '꙳': (3, 0x44), 'ꙴ': (4, 0x55), 'ꙵ': (5, 0x66),
    'ꙶ': (6, 0x77), 'ꙷ': (7, 0x88), 'ꙸ': (8, 0x99),
    'ꙹ': (12, 0xDD), 'ꙺ': (13, 0xEE), 'ꙻ': (14, 0xFF),
    '꙼': (15, 0xFE)
}

def hash_token(t):
    h = hashlib.sha256(t.encode("utf-8")).digest()
    raw = list(h)
    while len(raw) < DIM:
        h = hashlib.sha256(h).digest()
        raw.extend(list(h))
    return np.array(raw[:DIM], dtype=np.float32) / 255.0

def is_hieroglyph(c):
    cp = ord(c)
    return c in HIEROGLYPH_SEMANTICS or 0x13000 <= cp <= 0x1342F

def is_mayan_glyph(c):
    return c in MAYA_GLYPH_SEMANTICS

def hieroglyph_to_semantic_glyph(c):
    if c in HIEROGLYPH_SEMANTICS:
        g, b = HIEROGLYPH_SEMANTICS[c]
        return (g << 8) | b
    cp = ord(c)
    return ((cp % 16) << 8) | ((cp * 17) % 256)

def mayan_to_semantic_glyph(c):
    if c in MAYA_GLYPH_SEMANTICS:
        g, b = MAYA_GLYPH_SEMANTICS[c]
        return (g << 8) | b
    cp = ord(c)
    return ((cp % 16) << 8) | ((cp * 17) % 256)

def multilingual_to_vector(text):
    vec = np.zeros(DIM, dtype=np.float32)
    if not text:
        return vec
    for c in text:
        if is_hieroglyph(c):
            tok = hieroglyph_to_semantic_glyph(c)
            g, b = (tok >> 8) & 15, tok & 255
            vec += np.full(DIM, (g / 15.0) + (b / 255.0), dtype=np.float32) * 2.0
        elif is_mayan_glyph(c):
            tok = mayan_to_semantic_glyph(c)
            g, b = (tok >> 8) & 15, tok & 255
            vec += np.full(DIM, (g / 15.0) + (b / 255.0), dtype=np.float32) * 2.0
        else:
            vec += hash_token(c)
    return vec / max(1, len(text))

def vector_to_seed(text, start=4094, n=8):
    vec = multilingual_to_vector(text)
    out = [start]
    for i in range(n):
        v = float(vec[i % DIM]) * 255.0
        g = int(abs(v + i * 7)) % 15
        b = int((v * 31 + i * 17)) % 256
        out.append((g << 8) | b)
    return out
