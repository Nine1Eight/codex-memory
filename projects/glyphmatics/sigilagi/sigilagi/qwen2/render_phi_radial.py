#!/usr/bin/env python3
import sys
import math
import hashlib
from PIL import Image, ImageDraw, ImageFont

# ---------- CONFIG ----------
IMG_SIZE = 3000
CENTER = IMG_SIZE // 2
SPIRAL_SPACING = 14
ANGLE_STEP = 0.15
FONT_SIZE = 20
CHECKSUM_FONT_SIZE = 26
BACKGROUND = "black"
FOREGROUND = (255, 215, 0)

# ---------- INPUT ----------
if len(sys.argv) != 2:
    print("Usage: render_phi_radial.py <phi_stream_file>")
    sys.exit(1)

phi_file = sys.argv[1]

with open(phi_file, "r", encoding="utf-8") as f:
    glyph_stream = f.read().strip()

# ---------- CHECKSUM ----------
sha = hashlib.sha256(glyph_stream.encode("utf-8")).hexdigest()
checksum_text = f"[SHA256:{sha}]"

# ---------- CANVAS ----------
img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BACKGROUND)
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("DejaVuSans.ttf", FONT_SIZE)
    checksum_font = ImageFont.truetype("DejaVuSans.ttf", CHECKSUM_FONT_SIZE)
except:
    font = ImageFont.load_default()
    checksum_font = ImageFont.load_default()

# ---------- SPIRAL PAYLOAD ----------
angle = 0
radius = 50

for glyph in glyph_stream:
    x = CENTER + radius * math.cos(angle)
    y = CENTER + radius * math.sin(angle)

    draw.text((x, y), glyph, font=font, fill=FOREGROUND)

    angle += ANGLE_STEP
    radius += SPIRAL_SPACING * ANGLE_STEP

# ---------- CHECKSUM BAND ----------
ring_radius = IMG_SIZE // 2 - 80
circumference = 2 * math.pi * ring_radius
step = circumference / len(checksum_text)

for i, char in enumerate(checksum_text):
    theta = (i / len(checksum_text)) * 2 * math.pi
    x = CENTER + ring_radius * math.cos(theta)
    y = CENTER + ring_radius * math.sin(theta)
    draw.text((x, y), char, font=checksum_font, fill=FOREGROUND)

# ---------- SAVE ----------
out_file = phi_file.replace(".phi", "_sigil.png")
img.save(out_file)
print(f"[OK] Saved sigil to {out_file}")
