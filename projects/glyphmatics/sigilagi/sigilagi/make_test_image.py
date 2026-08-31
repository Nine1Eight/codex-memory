#!/usr/bin/env python3
import cv2
import numpy as np
import math

# =========================
# CONFIG
# =========================

BG = (0, 0, 0)

COLORS = {
    "ka": (255,255,255),
    "pa": (0,255,0),
    "bo": (0,165,255),
    "da": (255,255,0),
    "ri": (255,0,0),
}

TOKENS = [
    ("ka", None),
    ("pa", None),
    ("bo", None),
    ("da", None),
    ("ri", None),

    ("ka", 1),
    ("pa", 2),
    ("bo", 3),
    ("da", 4),
    ("ri", 5),

    ("ka", 6),
    ("pa", 7),
    ("bo", 8),
    ("da", 9),
    ("ri", 0),
]

CELL = 160
PAD = 40
COLS = 5
ROWS = (len(TOKENS)+COLS-1)//COLS

W = COLS*CELL + PAD*2
H = ROWS*CELL + PAD*2

img = np.zeros((H,W,3), dtype=np.uint8)
img[:] = BG

# =========================
# NUMERIC ENCODING (ROBUST)
# =========================

def draw_numeric(img, cx, cy, n):
    if n is None:
        return

    # zero = center hollow ring
    if n == 0:
        cv2.circle(img, (cx,cy), 12, (0,0,0), 3)
        return

    R = 28
    for i in range(n):
        ang = 2*np.pi*i/n
        px = int(cx + R*np.cos(ang))
        py = int(cy + R*np.sin(ang))
        cv2.circle(img, (px,py), 6, (0,0,0), -1)

# =========================
# SHAPES (DETECTION-STABLE)
# =========================

def draw_token(img, token, x, y):
    s, n = token
    c = COLORS[s]

    cx = x + CELL//2
    cy = y + CELL//2

    SIZE = 48

    if s == "ka":
        cv2.rectangle(img, (cx-SIZE,cy-SIZE),(cx+SIZE,cy+SIZE),c,-1)

    elif s == "pa":
        pts = np.array([
            [cx,cy-60],
            [cx-60,cy+45],
            [cx+60,cy+45]
        ],np.int32)
        cv2.fillPoly(img,[pts],c)

    elif s == "bo":
        cv2.circle(img,(cx,cy),52,c,-1)

    elif s == "da":
        pts = np.array([
            [cx,cy-60],
            [cx-60,cy],
            [cx,cy+60],
            [cx+60,cy]
        ],np.int32)
        cv2.fillPoly(img,[pts],c)

    elif s == "ri":
        r = 54
        pts = []
        for i in range(6):
            ang = math.radians(60*i)
            px = int(cx + r*np.cos(ang))
            py = int(cy + r*np.sin(ang))
            pts.append([px,py])
        cv2.fillPoly(img,[np.array(pts,np.int32)],c)

    draw_numeric(img,cx,cy,n)

# =========================
# GRID LAYOUT (ROW-MAJOR)
# =========================

for i,t in enumerate(TOKENS):
    r = i//COLS
    c = i%COLS
    x = PAD + c*CELL
    y = PAD + r*CELL
    draw_token(img,t,x,y)

# =========================
# WRITE
# =========================

cv2.imwrite("test_unisyl.png",img)
print("WROTE test_unisyl.png")
print("TOKENS:",len(TOKENS))
