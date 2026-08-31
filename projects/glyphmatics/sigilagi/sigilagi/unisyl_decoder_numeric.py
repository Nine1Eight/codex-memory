#!/usr/bin/env python3
import cv2
import numpy as np
import sys
import math

COLOR_MAP = {
    (255,255,255): "ka",
    (0,255,0): "pa",
    (0,165,255): "bo",
    (255,255,0): "da",
    (255,0,0): "ri",
}

COLOR_THRESHOLD = 100.0
MIN_AREA = 500
ROW_BUCKET = 120

def nearest_color(color):
    best = None
    best_d = 1e9
    c = np.array(color, dtype=np.float32)

    for k, v in COLOR_MAP.items():
        d = np.linalg.norm(c - np.array(k, dtype=np.float32))
        if d < best_d:
            best_d = d
            best = v

    return best if best_d < COLOR_THRESHOLD else "UNK"

def safe_center_color(img, cx, cy, radius=3):
    h, w = img.shape[:2]
    x0 = max(0, cx-radius)
    y0 = max(0, cy-radius)
    x1 = min(w, cx+radius+1)
    y1 = min(h, cy+radius+1)
    patch = img[y0:y1, x0:x1]
    if patch.size == 0:
        return (0,0,0)
    mean = patch.mean(axis=(0,1))
    return tuple(int(round(v)) for v in mean[:3])

def detect_numeric_dots(img, cx, cy):
    h, w = img.shape[:2]
    r = 26

    x0 = max(0, cx-r)
    y0 = max(0, cy-r)
    x1 = min(w, cx+r)
    y1 = min(h, cy+r)

    patch = img[y0:y1, x0:x1]
    if patch.size == 0:
        return None

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)

    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    small = 0
    ring_like = 0

    for c in cnts:
        area = cv2.contourArea(c)
        if 10 <= area <= 120:
            small += 1
        elif 120 < area < 260:
            ring_like += 1

    # zero marker = ring in center
    if ring_like == 1 and small == 0:
        return 0

    if small > 0:
        return small

    return None

def classify_shape(cnt):
    approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)
    sides = len(approx)

    if sides == 3:
        return "triangle"
    if sides == 4:
        return "square"
    if sides == 6:
        return "hex"

    area = cv2.contourArea(cnt)
    peri = cv2.arcLength(cnt, True)
    if peri == 0:
        return "unknown"

    circularity = 4 * math.pi * area / (peri * peri)
    if circularity > 0.80:
        return "circle"

    if sides == 4 or sides == 5:
        return "diamond"

    return "unknown"

def detect_nodes(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY)

    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    nodes = []

    for c in cnts:
        area = cv2.contourArea(c)
        if area < MIN_AREA:
            continue

        x, y, w, h = cv2.boundingRect(c)

        # ignore bottom text labels
        if h < 25:
            continue

        cx, cy = x + w//2, y + h//2
        color = safe_center_color(img, cx, cy)
        syllable = nearest_color(color)
        shape = classify_shape(c)
        num = detect_numeric_dots(img, cx, cy)

        if syllable == "UNK":
            continue

        token = syllable if num is None else f"{syllable}{num}"

        nodes.append({
            "pos": (cx, cy),
            "bbox": (x, y, w, h),
            "area": float(area),
            "shape": shape,
            "color_bgr": color,
            "numeric": num,
            "syllable": syllable,
            "token": token,
        })

    # row-first, then column
    nodes.sort(key=lambda n: (n["pos"][1] // ROW_BUCKET, n["pos"][0]))
    return nodes

class VM:
    def __init__(self):
        self.stack = []
        self.out = []

    def run(self, chain):
        print("\n=== EXECUTION ===")
        print("CHAIN:", "-".join(chain))

        for s in chain:
            if s.startswith("pa"):
                self.stack.append("obj")
            elif s.startswith("bo"):
                self.stack.append("Hello UniSyl UPL!")
            elif s.startswith("da"):
                if self.stack:
                    self.out.append(self.stack.pop())
            elif s.startswith("ri"):
                if self.out:
                    print("OUTPUT:", self.out[-1])

        return self.out

def main(path):
    img = cv2.imread(path)
    if img is None:
        print("ERR load")
        return

    nodes = detect_nodes(img)

    print("NODES:")
    for n in nodes:
        print(
            f"pos={n['pos']} "
            f"shape={n['shape']} "
            f"color={n['color_bgr']} "
            f"num={n['numeric']} "
            f"token={n['token']}"
        )

    chain = [n["token"] for n in nodes]
    vm = VM()
    vm.run(chain)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python unisyl_decoder_numeric.py <image>")
        sys.exit(1)
    main(sys.argv[1])
