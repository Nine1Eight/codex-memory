#!/usr/bin/env python3
import sys, math
from PIL import Image, ImageDraw, ImageFont

SIZE = 4000
CENTER = SIZE // 2
FONT_SIZE = 24
ANGLE_STEP = 0.12
SPACING = 12

if len(sys.argv) != 2:
    print("Usage: render_extractable_radial.py <wrapped.phi>")
    sys.exit(1)

with open(sys.argv[1], "r", encoding="utf-8") as f:
    glyphs = f.read().strip()

img = Image.new("RGB", (SIZE, SIZE), "black")
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("DejaVuSansMono.ttf", FONT_SIZE)
except:
    font = ImageFont.load_default()

angle = 0
radius = 50

for g in glyphs:
    x = CENTER + radius * math.cos(angle)
    y = CENTER + radius * math.sin(angle)
    draw.text((x, y), g, font=font, fill=(255,215,0))
    angle += ANGLE_STEP
    radius += SPACING * ANGLE_STEP

img.save("final_sigil.png")
print("[OK] Saved final_sigil.png")
