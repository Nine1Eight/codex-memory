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

data = sys.stdin.buffer.read()
n = int.from_bytes(len(data).to_bytes(8, "big") + data, "big")

out = []
while n:
    n, r = divmod(n, BASE)
    out.append(GLYPHS[r])

if not out:
    out.append(GLYPHS[0])

sys.stdout.write("".join(reversed(out)))
