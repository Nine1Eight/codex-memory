#!/usr/bin/env python3
import numpy as np
import hashlib
import json
import base64
from typing import Dict
from cryptography.fernet import Fernet

# =============================================
# G0: BB84 Simulation (Explicit Simulation Only)
# =============================================
def simulate_bb84(n_qubits: int = 1024, qber: float = 0.025) -> Dict:
    """SIMULATION ONLY. No real quantum channel. Returns sifted material + metadata."""
    alice_bits = np.random.randint(0, 2, n_qubits)
    alice_bases = np.random.choice(["+", "x"], n_qubits)

    bob_bases = np.random.choice(["+", "x"], n_qubits)
    bob_bits = np.zeros(n_qubits, dtype=int)

    for i in range(n_qubits):
        if alice_bases[i] == bob_bases[i]:
            bob_bits[i] = alice_bits[i] if np.random.rand() >= qber else 1 - alice_bits[i]
        else:
            bob_bits[i] = np.random.randint(0, 2)

    sifted = [int(alice_bits[i]) for i in range(n_qubits) if alice_bases[i] == bob_bases[i]]
    sifted_key = sifted[:256]

    if len(sifted_key) < 256:
        sifted_key += [0] * (256 - len(sifted_key))

    key_bytes = int("".join(map(str, sifted_key)), 2).to_bytes(32, "big")
    secure_key = hashlib.sha256(key_bytes).digest()

    return {
        "secure_key": secure_key,
        "sifted_bits": sifted_key,
        "metadata": {
            "raw": n_qubits,
            "sifted": len(sifted),
            "qber": qber,
            "simulation_only": True
        }
    }

# =============================================
# G2: Deterministic KDF + Encrypted Rehydration
# =============================================
def derive_fernet_key(anchor: str) -> bytes:
    salt = hashlib.sha256(anchor.encode()).digest()[:16]
    key_material = hashlib.pbkdf2_hmac(
        "sha256",
        anchor.encode(),
        salt,
        100000,
        dklen=32
    )
    return base64.urlsafe_b64encode(key_material)

# =============================================
# G7: Structured β-layer
# =============================================
def to_structured_braille(byte: int) -> list:
    bits = f"{byte:08b}"
    return [
        [bits[0], bits[3]],
        [bits[1], bits[4]],
        [bits[2], bits[5]],
        [bits[6], bits[7]],
    ]

# =============================================
# G15: Tri-Layer Sigil Generation
# =============================================
def generate_qkd_sigil(qkd_data: Dict, anchor_seed: str = "GLYPHMATICS_QKD_002") -> Dict:
    key = qkd_data["secure_key"]
    meta = qkd_data["metadata"]

    fernet_key = derive_fernet_key(anchor_seed)
    f = Fernet(fernet_key)
    encrypted_payload = f.encrypt(key)

    # G14 Lock A: plaintext key identity
    key_digest = hashlib.sha256(key + anchor_seed.encode()).hexdigest()

    # G14 Lock B: stored artifact integrity
    payload_digest = hashlib.sha256(encrypted_payload + anchor_seed.encode()).hexdigest()

    beta_lattice = [to_structured_braille(b) for b in encrypted_payload]

    hanzi_map = "一二三四五六七八九十百千万亿兆世界量子密钥分发"
    gamma_sequence = [
        hanzi_map[int.from_bytes(key[i:i+4], "big") % len(hanzi_map)]
        for i in range(0, len(key), 4)
    ]

    alpha_glyph = f"🔑⚡🌀QKD-SIGIL[{key_digest[:8]}]⚡🌀"

    return {
        "alpha": alpha_glyph,
        "beta": beta_lattice,
        "gamma": "".join(gamma_sequence),
        "digest": key_digest,
        "payload_digest": payload_digest,
        "vil_anchor": anchor_seed,
        "encrypted_payload": encrypted_payload.hex(),
        "qkd_metadata": meta,
        "rehydration_hint": f"vil-encoder-v1.2 + fernet(anchor)"
    }

# =============================================
# G14: Verifier + Rehydrator
# =============================================
def verify_payload_integrity(sigil: Dict, anchor_seed: str) -> bool:
    encrypted_payload = bytes.fromhex(sigil["encrypted_payload"])
    recomputed = hashlib.sha256(encrypted_payload + anchor_seed.encode()).hexdigest()
    return recomputed == sigil["payload_digest"]

def rehydrate_key(sigil: Dict, anchor_seed: str) -> bytes:
    if not verify_payload_integrity(sigil, anchor_seed):
        raise ValueError("G14 PAYLOAD LOCK FAILURE — ciphertext tamper detected")

    f = Fernet(derive_fernet_key(anchor_seed))
    key = f.decrypt(bytes.fromhex(sigil["encrypted_payload"]))

    recomputed_key_digest = hashlib.sha256(key + anchor_seed.encode()).hexdigest()
    if recomputed_key_digest != sigil["digest"]:
        raise ValueError("G14 KEY LOCK FAILURE — plaintext identity mismatch")

    return key

# =============================================
# G12: Full Execution
# =============================================
if __name__ == "__main__":
    print("🔥 GlyphMatics QKD Sigil UPGRADE v2 — Corrected G14 dual-lock\n")

    qkd_result = simulate_bb84()
    sigil = generate_qkd_sigil(qkd_result)

    print("✅ BB84 Simulation (explicitly labeled)")
    print(f"   QBER: {sigil['qkd_metadata']['qber']}")

    print("\n🌀 TRI-LAYER SIGIL GENERATED")
    print(f"α Visible:        {sigil['alpha']}")
    print(f"γ Temporal:       {sigil['gamma']}")
    print(f"β Lattice:        {len(sigil['beta'])} structured 2x4 cells")
    print(f"G14 Key Digest:   {sigil['digest'][:32]}...")
    print(f"G14 Payload Lock: {sigil['payload_digest'][:32]}...")

    recovered = rehydrate_key(sigil, sigil["vil_anchor"])
    assert recovered == qkd_result["secure_key"]

    print(f"\n✅ Rehydration verified: {recovered.hex()[:32]}... exact match")

    with open("qkd_sigil_upgraded.json", "w", encoding="utf-8") as f:
        json.dump(sigil, f, ensure_ascii=False, indent=2)

    print("\n💾 Saved to qkd_sigil_upgraded.json — ready for graph lineage")
