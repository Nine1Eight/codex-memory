#!/usr/bin/env python3
"""
UNISYL GRAPH EXECUTION RUNTIME v3.1
Adaptive row clustering + spatial DAG execution
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from production_unisyl_matrix import ProductionCapabilityMatrix

COLOR_MAP: Dict[Tuple[int, int, int], str] = {
    (255, 255, 255): "ka",
    (0, 255, 0):     "pa",
    (0, 165, 255):   "bo",
    (255, 255, 0):   "da",
    (255, 0, 0):     "ri",
}

COLOR_THRESH = 80.0
MIN_AREA = 100
ROW_MERGE_DIST = 35
CLUSTER_X_DIST = 45

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

def sample_color(img: np.ndarray, cx: int, cy: int, r: int = 2) -> Tuple[int, int, int]:
    h, w = img.shape[:2]
    x0 = max(0, cx - r)
    y0 = max(0, cy - r)
    x1 = min(w, cx + r + 1)
    y1 = min(h, cy + r + 1)
    patch = img[y0:y1, x0:x1]
    if patch.size == 0:
        return (0, 0, 0)
    mean = patch.mean(axis=(0, 1))
    return tuple(int(round(v)) for v in mean[:3])

def detect_raw_nodes(img: np.ndarray) -> List[Dict[str, Any]]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    raw_nodes: List[Dict[str, Any]] = []

    for c in contours:
        area = cv2.contourArea(c)
        if area < MIN_AREA:
            continue

        x, y, w, h = cv2.boundingRect(c)
        cx, cy = x + w // 2, y + h // 2
        color = sample_color(img, cx, cy)
        syll = nearest_color(color)

        if syll == "UNK":
            continue

        raw_nodes.append({
            "cx": cx,
            "cy": cy,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "area": float(area),
            "base": syll,
            "color_bgr": color,
        })

    raw_nodes.sort(key=lambda n: n["cy"])
    return raw_nodes

def assign_rows(raw_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adaptive row clustering by Y proximity.
    """
    if not raw_nodes:
        return raw_nodes

    row_centers: List[float] = []

    for node in raw_nodes:
        placed = False
        for i, yc in enumerate(row_centers):
            if abs(node["cy"] - yc) <= ROW_MERGE_DIST:
                node["row"] = i
                row_members = [n["cy"] for n in raw_nodes if n.get("row") == i] + [node["cy"]]
                row_centers[i] = sum(row_members) / len(row_members)
                placed = True
                break

        if not placed:
            node["row"] = len(row_centers)
            row_centers.append(float(node["cy"]))

    raw_nodes.sort(key=lambda n: (n["row"], n["cx"]))
    return raw_nodes

def consolidate_nodes(raw_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not raw_nodes:
        return []

    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = [raw_nodes[0]]

    for node in raw_nodes[1:]:
        last = current[-1]
        same_row = node["row"] == last["row"]
        same_base = node["base"] == last["base"]
        close_x = abs(node["cx"] - last["cx"]) < CLUSTER_X_DIST

        if same_row and same_base and close_x:
            current.append(node)
        else:
            groups.append(current)
            current = [node]

    groups.append(current)

    nodes: List[Dict[str, Any]] = []
    for i, group in enumerate(groups):
        base = group[0]["base"]
        row = group[0]["row"]
        xs = [g["cx"] for g in group]
        ys = [g["cy"] for g in group]

        nodes.append({
            "id": f"g{i}",
            "base": base,
            "depth": len(group),
            "token": f"{base}{len(group)}",
            "cx": int(round(sum(xs) / len(xs))),
            "cy": int(round(sum(ys) / len(ys))),
            "row": row,
            "members": len(group),
        })

    nodes.sort(key=lambda n: (n["row"], n["cx"]))
    return nodes

def build_edges(nodes: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    edges: List[Tuple[str, str]] = []
    rows: Dict[int, List[Dict[str, Any]]] = {}

    for n in nodes:
        rows.setdefault(n["row"], []).append(n)

    for r in sorted(rows.keys()):
        row_nodes = sorted(rows[r], key=lambda n: n["cx"])
        for a, b in zip(row_nodes, row_nodes[1:]):
            edges.append((a["id"], b["id"]))

    sorted_rows = sorted(rows.keys())
    for r1, r2 in zip(sorted_rows, sorted_rows[1:]):
        row1 = sorted(rows[r1], key=lambda n: n["cx"])
        row2 = sorted(rows[r2], key=lambda n: n["cx"])
        if row1 and row2:
            edges.append((row1[-1]["id"], row2[0]["id"]))

    return edges

def topo_order(nodes: List[Dict[str, Any]], edges: List[Tuple[str, str]]) -> List[str]:
    indeg = {n["id"]: 0 for n in nodes}
    adj = {n["id"]: [] for n in nodes}

    for a, b in edges:
        adj[a].append(b)
        indeg[b] += 1

    queue = sorted([nid for nid, d in indeg.items() if d == 0])
    out: List[str] = []

    while queue:
        nid = queue.pop(0)
        out.append(nid)
        for m in sorted(adj[nid]):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
                queue.sort()

    return out

def build_direct_chain(nodes: List[Dict[str, Any]], order: List[str]) -> str:
    lookup = {n["id"]: n for n in nodes}
    return "-".join(lookup[nid]["token"] for nid in order if nid in lookup)

def summarize_graph(nodes: List[Dict[str, Any]], edges: List[Tuple[str, str]]) -> Dict[str, Any]:
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "bases": [n["base"] for n in nodes],
        "depths": [n["depth"] for n in nodes],
        "rows": sorted(set(n["row"] for n in nodes)),
        "depth_sum": sum(n["depth"] for n in nodes),
    }

def run(image_path: str) -> None:
    img = cv2.imread(image_path)
    if img is None:
        print("ERROR: cannot load image")
        return

    raw_nodes = detect_raw_nodes(img)
    raw_nodes = assign_rows(raw_nodes)
    nodes = consolidate_nodes(raw_nodes)
    edges = build_edges(nodes)
    order = topo_order(nodes, edges)
    direct_chain = build_direct_chain(nodes, order)
    summary = summarize_graph(nodes, edges)

    print("\n[RAW NODES]")
    for n in raw_nodes:
        print(
            f"row={n['row']} pos=({n['cx']},{n['cy']}) "
            f"base={n['base']} color={n['color_bgr']} area={n['area']:.1f}"
        )

    print("\n[GRAPH NODES]")
    for n in nodes:
        print(
            f"id={n['id']} row={n['row']} pos=({n['cx']},{n['cy']}) "
            f"token={n['token']} members={n['members']}"
        )

    print("\n[GRAPH EDGES]")
    for a, b in edges:
        print(f"{a} -> {b}")

    print("\n[TOPO ORDER]")
    print(order)

    print("\n[DIRECT CHAIN]")
    print(direct_chain)

    print("\n[GRAPH SUMMARY]")
    print(summary)

    system = ProductionCapabilityMatrix()
    result = system.execute_glyphs(direct_chain)

    print("\n[FINAL OUTPUT]")
    print(result)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python unisyl_graph_runtime.py <image.png>")
        raise SystemExit(1)
    run(sys.argv[1])
