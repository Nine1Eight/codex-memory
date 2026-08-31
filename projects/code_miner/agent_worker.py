import ast
import hashlib
from grammar_engine import build_ast
from sandbox_runner import execute_source
from execution_coordinates import build_coordinates

def run_agent(genome):
    module = build_ast(genome)
    source = ast.unparse(module)

    result = execute_source(source)

    coordinates = build_coordinates(module, result)

    return {
        "genome": genome,
        "source": source,
        "coordinates": coordinates,
        "hash": hashlib.sha256(source.encode()).hexdigest()
    }
