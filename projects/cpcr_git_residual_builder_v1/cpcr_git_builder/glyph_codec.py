from __future__ import annotations

BRAILLE_BASE = 0x2800


def bytes_to_braille(data: bytes) -> str:
    return "".join(chr(BRAILLE_BASE + b) for b in data)


def braille_to_bytes(glyphs: str) -> bytes:
    out = bytearray()
    for ch in glyphs:
        code = ord(ch)
        if not (BRAILLE_BASE <= code <= BRAILLE_BASE + 255):
            raise ValueError(f"not an 8-bit braille byte glyph: U+{code:04X}")
        out.append(code - BRAILLE_BASE)
    return bytes(out)


def text_to_glyphs(text: str) -> str:
    return bytes_to_braille(text.encode("utf-8"))


def glyphs_to_text(glyphs: str) -> str:
    return braille_to_bytes(glyphs).decode("utf-8")


def text_to_binary(text: str) -> str:
    return " ".join(f"{b:08b}" for b in text.encode("utf-8"))


def binary_to_text(bits: str) -> str:
    clean = bits.replace(" ", "")
    if len(clean) % 8:
        raise ValueError("binary length must be a multiple of 8")
    return bytes(int(clean[i:i+8], 2) for i in range(0, len(clean), 8)).decode("utf-8")
