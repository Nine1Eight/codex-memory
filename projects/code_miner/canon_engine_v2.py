#!/usr/bin/env python3
import hashlib
import hmac
import os
import argparse
import random

BASE = 111


# -----------------------------
# Canon Loading
# -----------------------------

def extract_glyphs(path):
    with open(path, "r", encoding="utf-8") as f:
        return [c for c in f.read() if not c.isspace()]


def load_canon(dir_path):
    visible = extract_glyphs(os.path.join(dir_path, "canon_visible_111.idx"))
    invisible = extract_glyphs(os.path.join(dir_path, "canon_invisible_111.idx"))
    vocab = extract_glyphs(os.path.join(dir_path, "canon_vocab_111.idx"))

    if not (len(visible) == len(invisible) == len(vocab) == BASE):
        raise ValueError("Canonical sets must each contain 111 glyphs.")

    return visible, invisible, vocab


# -----------------------------
# Base111 Encoding / Decoding
# -----------------------------

def base111_encode(data: bytes, glyphset):
    n = int.from_bytes(data, "big")
    if n == 0:
        return glyphset[0]

    out = []
    while n:
        n, r = divmod(n, BASE)
        out.append(glyphset[r])
    return "".join(reversed(out))


def base111_decode(text: str, glyphset):
    index = {g: i for i, g in enumerate(glyphset)}
    n = 0
    for ch in text:
        n = n * BASE + index[ch]
    byte_len = (n.bit_length() + 7) // 8
    return n.to_bytes(byte_len, "big")


# -----------------------------
# Deterministic Entropy
# -----------------------------

def deterministic_entropy(payload: bytes):
    return hashlib.sha256(payload).digest()[:16]


# -----------------------------
# HMAC Keystore Signing
# -----------------------------

def sign_with_keystore(data: bytes, keystore_path):
    with open(keystore_path, "rb") as f:
        key = f.read().strip()
    return hmac.new(key, data, hashlib.sha256).digest()


# -----------------------------
# Merkle Chunking
# -----------------------------

def merkle_root(payload: bytes, chunk_size=32):
    chunks = [payload[i:i+chunk_size] for i in range(0, len(payload), chunk_size)]
    hashes = [hashlib.sha256(c).digest() for c in chunks]

    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [
            hashlib.sha256(hashes[i] + hashes[i+1]).digest()
            for i in range(0, len(hashes), 2)
        ]
    return hashes[0]


# -----------------------------
# Coordinate Builder
# -----------------------------

def build_coordinate(payload: bytes, visible, keystore_path):
    entropy = deterministic_entropy(payload)
    root = merkle_root(payload)
    body = payload + entropy + root

    signature = sign_with_keystore(body, keystore_path)

    return {
        "structure": base111_encode(payload, visible),
        "entropy": base111_encode(entropy, visible),
        "merkle": base111_encode(root, visible),
        "signature": base111_encode(signature, visible),
    }


# -----------------------------
# Autonomous Mining Loop
# -----------------------------

def mutate_payload(payload: bytes):
    data = bytearray(payload)
    if len(data) == 0:
        data = bytearray(b"seed")
    i = random.randint(0, len(data)-1)
    data[i] ^= random.randint(1, 255)
    return bytes(data)


def mining_loop(initial_payload, visible, keystore_path, iterations=10):
    payload = initial_payload
    for i in range(iterations):
        payload = mutate_payload(payload)
        coord = build_coordinate(payload, visible, keystore_path)
        print(f"\n[Iteration {i+1}]")
        print("Structure :", coord["structure"][:20], "...")
        print("Signature :", coord["signature"][:20], "...")


# -----------------------------
# Main
# -----------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canon-dir", required=True)
    parser.add_argument("--keystore", required=True)
    parser.add_argument("--mine", action="store_true")
    parser.add_argument("payload", nargs="?", default="canonical-seed")
    args = parser.parse_args()

    visible, invisible, vocab = load_canon(args.canon_dir)

    payload = args.payload.encode("utf-8")

    if args.mine:
        mining_loop(payload, visible, args.keystore)
    else:
        coord = build_coordinate(payload, visible, args.keystore)

        print("\n=== CANONICAL COORDINATE v2 ===")
        print("Structure :", coord["structure"])
        print("Entropy   :", coord["entropy"])
        print("Merkle    :", coord["merkle"])
        print("Signature :", coord["signature"])


if __name__ == "__main__":
    main()
