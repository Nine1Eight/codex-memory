import ast
import hashlib
from sandbox_runner import execute_source

def normalize_ast(module):
    ast.fix_missing_locations(module)
    return module

def structural_complexity(module):
    return len(list(ast.walk(module)))

def evaluate_module(module):
    module = normalize_ast(module)
    source = ast.unparse(module)
    result = execute_source(source)

    complexity = structural_complexity(module)

    return {
        "source": source,
        "hash": hashlib.sha256(source.encode()).hexdigest(),
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "duration": result["duration"],
        "complexity": complexity
    }
