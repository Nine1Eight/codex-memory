#!/usr/bin/env python3
import sys
import hashlib

GLYPHS = (
    ""
    ""
    ""
    ""
    "⠀⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟"
    "⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿"
    "⡀⡁⡂⡃⡄⡅⡆⡇⡈⡉⡊⡋⡌⡍⡎⡏⡐⡑⡒⡓⡔⡕⡖⡗⡘⡙⡚⡛⡜⡝⡞⡟"
    "⡠⡡⡢⡣⡤⡥⡦⡧⡨⡩⡪⡫⡬⡭⡮"
    "✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋★☆✩✪✫✬✭✮✯✰✱✲✳✴✵"
    "☀☁☂☃☄☼☽☾♠♡♣♤♦❤⚡⚔☯⚛⚗⚙⚒⚚⚕⚖⚘⊏⊐⚓⚑〇⟁"
    "⧖⧗⧘⧙⧚⧛⟐⟑⟒⟓⟔⟕⟖⟗⟘⟙⟜⟝⟞⟟⟠⟡⟢⟣⟤⟥⟦⟧⟨⟩⟪⟫⟬⟭⟮⟯⦀⦁⦂⦃⦄⦅⦆"
)

BASE = len(GLYPHS)

def phi_encode_bytes(data: bytes):
    n = int.from_bytes(data, "big")
    out = []
    while n:
        n, r = divmod(n, BASE)
        out.append(GLYPHS[r])
    return "".join(reversed(out)) or GLYPHS[0]

if len(sys.argv) != 2:
    print("Usage: build_self_verifying_phi.py <phi_stream_file>")
    sys.exit(1)

with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = f.read().strip()

payload_hash = hashlib.sha256(payload.encode("utf-8")).digest()
checksum_phi = phi_encode_bytes(payload_hash)

final_stream = f"⟦START⟧{payload}⟦END⟧{checksum_phi}"

with open("wrapped.phi", "w", encoding="utf-8") as out:
    out.write(final_stream)

print("[OK] Created wrapped.phi")
