#!/usr/bin/env python3
import hashlib
import hmac
import os
import argparse
import json
from collections import Counter
from math import log2

BASE = 111


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

    return visible


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
# Deterministic Entropy
# =========================================================

def deterministic_entropy(payload: bytes):
    return hashlib.sha256(payload).digest()[:16]


# =========================================================
# Merkle
# =========================================================

def merkle_root(payload: bytes):
    h = hashlib.sha256(payload).digest()
    return h


# =========================================================
# Keystore
# =========================================================

def sign_with_keystore(data: bytes, keystore_path):
    with open(keystore_path, "rb") as f:
        key = f.read().strip()
    return hmac.new(key, data, hashlib.sha256).digest()

def verify_signature(data: bytes, signature: bytes, keystore_path):
    expected = sign_with_keystore(data, keystore_path)
    return hmac.compare_digest(expected, signature)


# =========================================================
# CVM Interpreter
# =========================================================

class CVM:
    def __init__(self):
        self.stack = []

    def run(self, bytecode: bytes):
        pc = 0
        while pc < len(bytecode):
            op = bytecode[pc]
            pc += 1

            if op == 0x00:  # NOP
                continue

            elif op == 0x01:  # PUSH
                val = bytecode[pc]
                pc += 1
                self.stack.append(val)

            elif op == 0x02:  # ADD
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append((a + b) & 0xFF)

            elif op == 0x03:  # SUB
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append((a - b) & 0xFF)

            elif op == 0x04:  # MUL
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append((a * b) & 0xFF)

            elif op == 0x05:  # DIV
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append((a // b) & 0xFF)

            elif op == 0x06:  # PRINT
                val = self.stack.pop()
                print("CVM OUTPUT:", val)

            elif op == 0xFF:  # HALT
                break

            else:
                raise ValueError(f"Unknown opcode {hex(op)}")

        return self.stack


# =========================================================
# Coordinate Builder
# =========================================================

def build_coordinate(payload: bytes, visible, keystore_path):
    entropy = deterministic_entropy(payload)
    merkle = merkle_root(payload)
    body = payload + entropy + merkle
    signature = sign_with_keystore(body, keystore_path)

    return {
        "structure": base111_encode(payload, visible),
        "entropy": base111_encode(entropy, visible),
        "merkle": base111_encode(merkle, visible),
        "signature": base111_encode(signature, visible),
    }


# =========================================================
# Execution
# =========================================================

def execute_coordinate(structure, entropy, merkle, signature,
                       visible, keystore_path):

    payload = base111_decode(structure, visible)
    entropy_b = base111_decode(entropy, visible)
    merkle_b = base111_decode(merkle, visible)
    sig_b = base111_decode(signature, visible)

    expected_entropy = deterministic_entropy(payload)
    expected_merkle = merkle_root(payload)
    body = payload + expected_entropy + expected_merkle

    if not (
        entropy_b == expected_entropy and
        merkle_b == expected_merkle and
        verify_signature(body, sig_b, keystore_path)
    ):
        raise ValueError("Coordinate verification failed.")

    print("VERIFIED — EXECUTING CVM\n")

    vm = CVM()
    vm.run(payload)


# =========================================================
# Main
# =========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canon-dir", required=True)
    parser.add_argument("--keystore", required=True)
    parser.add_argument("--exec", nargs=4)
    parser.add_argument("payload", nargs="?")
    args = parser.parse_args()

    visible = load_canon(args.canon_dir)

    if args.exec:
        execute_coordinate(
            args.exec[0],
            args.exec[1],
            args.exec[2],
            args.exec[3],
            visible,
            args.keystore
        )
        return

    payload = (args.payload or "").encode("utf-8")
    coord = build_coordinate(payload, visible, args.keystore)

    print("\n=== CANONICAL COORDINATE v4 ===")
    print("Structure :", coord["structure"])
    print("Entropy   :", coord["entropy"])
    print("Merkle    :", coord["merkle"])
    print("Signature :", coord["signature"])


if __name__ == "__main__":
    main()
