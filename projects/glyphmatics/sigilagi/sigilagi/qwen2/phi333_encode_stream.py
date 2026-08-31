#!/usr/bin/env python3
import sys

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

# Rolling accumulator in base-256 → base-333
acc = 0
acc_bits = 0

read = sys.stdin.buffer.read

while True:
    chunk = read(1024 * 1024)
    if not chunk:
        break
    for b in chunk:
        acc = (acc << 8) | b
        acc_bits += 8
        while acc_bits >= 9:  # enough entropy to emit base-333 digit
            acc_bits -= 9
            digit = (acc >> acc_bits) % BASE
            sys.stdout.write(GLYPHS[digit])

# Flush remaining bits
if acc_bits > 0:
    sys.stdout.write(GLYPHS[(acc << (9 - acc_bits)) % BASE])
