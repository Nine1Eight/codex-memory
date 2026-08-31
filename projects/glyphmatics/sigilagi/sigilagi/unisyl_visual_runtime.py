#!/usr/bin/env python3
"""
UNISYL VISUAL RUNTIME v2.6
Image -> Glyph -> Depth Encoding -> Direct Capability Execution
No normalization layer
"""

import cv2
import numpy as np
from typing import List, Tuple
from production_unisyl_matrix import ProductionCapabilityMatrix

COLOR_MAP = {
    (255,255,255): "ka",
    (0,255,0):     "pa",
    (0,165,255):   "bo",
    (255,255,0):   "da",
    (255,0,0):     "ri",
}

COLOR_THRESH = 80.0
MIN_AREA = 100
CLUSTER_DIST = 40

def nearest_color(color: Tuple[int, int, int]) -> str:
    best = None
    best_dist = 1e9
    c = np.array(color, dtype=np.float32)

    for k, v in COLOR_MAP.items():
        dist = float(np.linalg.norm(c - np.array(k, dtype=np.float32)))
        if dist < best_dist:
            best_dist = dist
            best = v

    if best is None or best_dist > COLOR_THRESH:
        return "UNK"
    return best

def sample_color(img, cx, cy, r=2):
    h, w = img.shape[:2]
    x0 = max(0, cx-r)
    y0 = max(0, cy-r)
    x1 = min(w, cx+r+1)
    y1 = min(h, cy+r+1)

    patch = img[y0:y1, x0:x1]
    if patch.size == 0:
        return (0, 0, 0)

    mean = patch.mean(axis=(0, 1))
    return tuple(int(round(v)) for v in mean[:3])

def detect(img) -> List[str]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    raw_nodes = []

    for c in contours:
        if cv2.contourArea(c) < MIN_AREA:
            continue

        x, y, w, h = cv2.boundingRect(c)
        cx, cy = x + w // 2, y + h // 2

        color = sample_color(img, cx, cy)
        syll = nearest_color(color)

        raw_nodes.append((cx, syll))

    raw_nodes.sort(key=lambda n: n[0])

    clusters = []
    current = []

    for node in raw_nodes:
        if not current:
            current.append(node)
            continue

        if abs(node[0] - current[-1][0]) < CLUSTER_DIST:
            current.append(node)
        else:
            clusters.append(current)
            current = [node]

    if current:
        clusters.append(current)

    tokens = []
    for group in clusters:
        valid = [g[1] for g in group if g[1] != "UNK"]
        if not valid:
            continue

        base = valid[0]
        depth = len(valid)
        tokens.append(f"{base}{depth}")

    return tokens

def run(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        print("ERROR: cannot load image")
        return

    tokens = detect(img)
    direct_chain = "-".join(tokens)

    print("\n[DETECTED TOKENS]")
    print(tokens)

    print("\n[DIRECT CHAIN]")
    print(direct_chain)

    system = ProductionCapabilityMatrix()
    result = system.execute_glyphs(direct_chain)

    print("\n[FINAL OUTPUT]")
    print(result)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python unisyl_visual_runtime.py <image.png>")
        raise SystemExit(1)

    run(sys.argv[1])
