import ast
import hashlib
import math
import collections

def ast_metrics(module):
    nodes = list(ast.walk(module))
    node_count = len(nodes)
    depth = max_depth(module)
    return node_count, depth

def max_depth(node, level=0):
    if not isinstance(node, ast.AST):
        return level
    children = list(ast.iter_child_nodes(node))
    if not children:
        return level
    return max(max_depth(c, level+1) for c in children)

def stdout_entropy(stdout):
    if not stdout:
        return 0
    freq = collections.Counter(stdout)
    total = len(stdout)
    entropy = 0
    for v in freq.values():
        p = v / total
        entropy -= p * math.log2(p)
    return entropy

def build_coordinates(module, exec_result):
    node_count, depth = ast_metrics(module)

    stdout = exec_result["stdout"]

    coordinates = {
        "ast_hash": hashlib.sha256(ast.unparse(module).encode()).hexdigest(),
        "node_count": node_count,
        "depth": depth,
        "duration": exec_result["duration"],
        "entropy": stdout_entropy(stdout),
        "returncode": exec_result["returncode"]
    }

    return coordinates
