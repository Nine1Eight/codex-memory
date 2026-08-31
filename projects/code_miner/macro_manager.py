import ast
import hashlib
import json
import os
import time
import tempfile

MACRO_FILE = "grammar_macros.json"
MIN_SUBTREE_SIZE = 3
PRUNE_THRESHOLD = 0.5

def safe_load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except:
        # Corrupted or partial file — ignore safely
        return {}

def safe_write_json(path, data):
    dir_name = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        dir=dir_name
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = tmp.name

    os.replace(tmp_path, path)  # atomic on POSIX

def load_macros():
    macros = safe_load_json(MACRO_FILE)

    # Schema upgrade safety
    for k, v in macros.items():
        if "fitness_avg" not in v:
            total = v.get("fitness_total", 0)
            count = v.get("count", 1)
            v["fitness_avg"] = total / max(count, 1)
        if "usage" not in v:
            v["usage"] = 0
        if "lineage" not in v:
            v["lineage"] = []
        if "created" not in v:
            v["created"] = time.time()

    return macros

def save_macros(macros):
    safe_write_json(MACRO_FILE, macros)

def canonicalize(node):
    return ast.dump(node, annotate_fields=False)

def extract_subtrees(module):
    subtrees = []
    for node in ast.walk(module):
        children = list(ast.iter_child_nodes(node))
        if len(children) >= MIN_SUBTREE_SIZE:
            subtrees.append(node)
    return subtrees

def promote_from_elite(source_code, fitness_score):
    module = ast.parse(source_code)
    macros = load_macros()

    for subtree in extract_subtrees(module):
        canon = canonicalize(subtree)
        h = hashlib.sha256(canon.encode()).hexdigest()

        if h not in macros:
            macros[h] = {
                "count": 1,
                "fitness_total": fitness_score,
                "fitness_avg": fitness_score,
                "code": ast.unparse(subtree),
                "created": time.time(),
                "usage": 0,
                "lineage": []
            }
        else:
            m = macros[h]
            m["count"] += 1
            m["fitness_total"] += fitness_score
            m["fitness_avg"] = m["fitness_total"] / m["count"]

    save_macros(macros)

def prune_macros():
    macros = load_macros()
    if not macros:
        return

    ranked = sorted(
        macros.items(),
        key=lambda x: x[1]["fitness_avg"],
        reverse=True
    )

    top_score = ranked[0][1]["fitness_avg"]

    pruned = {
        k: v for k, v in macros.items()
        if v["fitness_avg"] >= top_score * PRUNE_THRESHOLD
    }

    save_macros(pruned)

def record_macro_usage(macro_hash, parent_hash):
    macros = load_macros()
    if macro_hash in macros:
        macros[macro_hash]["usage"] += 1
        macros[macro_hash]["lineage"].append(parent_hash)
        save_macros(macros)
