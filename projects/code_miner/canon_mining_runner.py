#!/usr/bin/env python3
import hashlib
import os
import sys
import argparse

BASE = 111


def extract_glyphs(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found.")

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Remove whitespace only
    glyphs = [c for c in raw if not c.isspace()]

    return glyphs


def base111_encode(data: bytes, glyphset):
    n = int.from_bytes(data, "big")
    if n == 0:
        return glyphset[0]

    out = []
    while n > 0:
        n, r = divmod(n, BASE)
        out.append(glyphset[r])
    return "".join(reversed(out))


def hash111(data: bytes, glyphset):
    h = hashlib.sha256(data).digest()
    return base111_encode(h, glyphset)


def build_coordinate(payload: bytes, glyphset):
    entropy = os.urandom(16)
    body = payload + entropy
    signature = hash111(body, glyphset)

    return {
        "structure": base111_encode(payload, glyphset),
        "entropy": base111_encode(entropy, glyphset),
        "signature": signature
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canon-dir", required=True)
    parser.add_argument("payload", nargs="?", default="canonical-mining-test")
    args = parser.parse_args()

    canon_dir = args.canon_dir

    visible = extract_glyphs(os.path.join(canon_dir, "canon_visible_111.idx"))
    invisible = extract_glyphs(os.path.join(canon_dir, "canon_invisible_111.idx"))
    vocab = extract_glyphs(os.path.join(canon_dir, "canon_vocab_111.idx"))

    print(f"Visible count  : {len(visible)}")
    print(f"Invisible count: {len(invisible)}")
    print(f"Vocab count    : {len(vocab)}")

    if len(visible) != BASE:
        raise ValueError("Visible canon must contain exactly 111 glyphs.")
    if len(invisible) != BASE:
        raise ValueError("Invisible canon must contain exactly 111 glyphs.")
    if len(vocab) != BASE:
        raise ValueError("Vocab canon must contain exactly 111 glyphs.")

    payload_bytes = args.payload.encode("utf-8")
    coord = build_coordinate(payload_bytes, visible)

    print("\n=== CANONICAL COORDINATE ===")
    print("Structure :", coord["structure"])
    print("Entropy   :", coord["entropy"])
    print("Signature :", coord["signature"])


if __name__ == "__main__":
    main()
