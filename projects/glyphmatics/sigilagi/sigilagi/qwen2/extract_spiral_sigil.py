#!/usr/bin/env python3
import sys, math
from PIL import Image, ImageDraw, ImageFont

SIZE = 4000
CENTER = SIZE // 2
FONT_SIZE = 24
ANGLE_STEP = 0.12
SPACING = 12
SAMPLE_BOX = 28
FOREGROUND = (255,215,0)
BACKGROUND = (0,0,0)

CANON = (
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

if len(sys.argv) != 2:
    print("Usage: extract_spiral_sigil.py <final_sigil.png>")
    sys.exit(1)

img = Image.open(sys.argv[1]).convert("RGB")

try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", FONT_SIZE)
except:
    font = ImageFont.load_default()

# ---------- BUILD ATLAS USING RAW BYTES ----------
atlas = {}

for g in CANON + "⟦START⟧⟦END⟧":
    tmp = Image.new("RGB", (SAMPLE_BOX, SAMPLE_BOX), BACKGROUND)
    d = ImageDraw.Draw(tmp)
    d.text((SAMPLE_BOX//4, SAMPLE_BOX//4), g, font=font, fill=FOREGROUND)
    atlas[g] = tmp.tobytes()

# ---------- SPIRAL REPLAY ----------
angle = 0
radius = 50
extracted = []

while radius < SIZE // 2:
    x = CENTER + radius * math.cos(angle)
    y = CENTER + radius * math.sin(angle)

    box = (
        int(x - SAMPLE_BOX/2),
        int(y - SAMPLE_BOX/2),
        int(x + SAMPLE_BOX/2),
        int(y + SAMPLE_BOX/2)
    )

    crop = img.crop(box)
    crop_bytes = crop.tobytes()

    # Skip empty
    if all(b == 0 for b in crop_bytes):
        angle += ANGLE_STEP
        radius += SPACING * ANGLE_STEP
        continue

    best_score = float("inf")
    best_char = None

    for g, template in atlas.items():
        diff = sum(abs(p - t) for p, t in zip(crop_bytes, template))
        if diff < best_score:
            best_score = diff
            best_char = g

    if best_char:
        extracted.append(best_char)

    angle += ANGLE_STEP
    radius += SPACING * ANGLE_STEP

stream = "".join(extracted)

print("[OK] Extraction complete.")
print("Recovered glyph count:", len(stream))

with open("recovered_stream.phi", "w", encoding="utf-8") as f:
    f.write(stream)
