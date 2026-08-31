#!/usr/bin/env python3
import hashlib
import hmac
import os
import argparse
import json
import random
from collections import Counter
from math import log2

BASE = 111
REGISTRY_FILE = "coordinate_registry.json"


# =========================================================
# Canon Loading
# =========================================================

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


# =========================================================
# Base111 Encode / Decode
# =========================================================

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


# =========================================================
# Entropy
# =========================================================

def deterministic_entropy(payload: bytes):
    return hashlib.sha256(payload).digest()[:16]

def shannon_entropy(data: bytes):
    if not data:
        return 0
    counts = Counter(data)
    total = len(data)
    return -sum((c/total) * log2(c/total) for c in counts.values())


# =========================================================
# Merkle Tree
# =========================================================

def merkle_root(payload: bytes, chunk_size=32):
    chunks = [payload[i:i+chunk_size] for i in range(0, len(payload), chunk_size)]
    hashes = [hashlib.sha256(c).digest() for c in chunks]

    if not hashes:
        return hashlib.sha256(b'').digest()

    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [
            hashlib.sha256(hashes[i] + hashes[i+1]).digest()
            for i in range(0, len(hashes), 2)
        ]
    return hashes[0]


# =========================================================
# Keystore Signing
# =========================================================

def sign_with_keystore(data: bytes, keystore_path):
    with open(keystore_path, "rb") as f:
        key = f.read().strip()
    return hmac.new(key, data, hashlib.sha256).digest()

def verify_signature(data: bytes, signature: bytes, keystore_path):
    expected = sign_with_keystore(data, keystore_path)
    return hmac.compare_digest(expected, signature)


# =========================================================
# Coordinate Builder
# =========================================================

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
        "entropy_score": shannon_entropy(payload),
        "coordinate_id": hashlib.sha256(payload).hexdigest()
    }


# =========================================================
# Verification
# =========================================================

def verify_coordinate(structure, entropy, merkle, signature,
                      visible, keystore_path):

    payload = base111_decode(structure, visible)
    entropy_bytes = base111_decode(entropy, visible)
    merkle_bytes = base111_decode(merkle, visible)
    signature_bytes = base111_decode(signature, visible)

    expected_entropy = deterministic_entropy(payload)
    expected_merkle = merkle_root(payload)
    body = payload + expected_entropy + expected_merkle

    valid = (
        entropy_bytes == expected_entropy and
        merkle_bytes == expected_merkle and
        verify_signature(body, signature_bytes, keystore_path)
    )

    return valid


# =========================================================
# Registry
# =========================================================

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        return {}
    with open(REGISTRY_FILE, "r") as f:
        return json.load(f)

def save_registry(reg):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=2)

def register_coordinate(coord):
    reg = load_registry()
    reg[coord["coordinate_id"]] = coord
    save_registry(reg)


# =========================================================
# Mining Loop
# =========================================================

def mutate_payload(payload: bytes):
    data = bytearray(payload)
    if len(data) == 0:
        data = bytearray(b"seed")
    i = random.randint(0, len(data)-1)
    data[i] ^= random.randint(1, 255)
    return bytes(data)

def mining_loop(initial_payload, visible, keystore_path, iterations=20):
    best_score = -1
    payload = initial_payload

    for i in range(iterations):
        candidate = mutate_payload(payload)
        score = shannon_entropy(candidate)

        if score > best_score:
            best_score = score
            payload = candidate

        coord = build_coordinate(payload, visible, keystore_path)
        register_coordinate(coord)

        print(f"\n[Iteration {i+1}]")
        print("Entropy Score:", round(coord["entropy_score"], 4))
        print("Coordinate ID:", coord["coordinate_id"][:16])
        print("Signature:", coord["signature"][:20], "...")


# =========================================================
# Main
# =========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canon-dir", required=True)
    parser.add_argument("--keystore", required=True)
    parser.add_argument("--verify", nargs=4)
    parser.add_argument("--mine", action="store_true")
    parser.add_argument("payload", nargs="?")
    args = parser.parse_args()

    visible, invisible, vocab = load_canon(args.canon_dir)

    if args.verify:
        valid = verify_coordinate(
            args.verify[0],
            args.verify[1],
            args.verify[2],
            args.verify[3],
            visible,
            args.keystore
        )
        print("VALID" if valid else "INVALID")
        return

    payload = (args.payload or "canonical-seed").encode("utf-8")

    if args.mine:
        mining_loop(payload, visible, args.keystore)
    else:
        coord = build_coordinate(payload, visible, args.keystore)
        register_coordinate(coord)

        print("\n=== CANONICAL COORDINATE v3 ===")
        print("Structure :", coord["structure"])
        print("Entropy   :", coord["entropy"])
        print("Merkle    :", coord["merkle"])
        print("Signature :", coord["signature"])
        print("Entropy Score:", round(coord["entropy_score"], 4))
        print("Coordinate ID:", coord["coordinate_id"])


if __name__ == "__main__":
    main()
