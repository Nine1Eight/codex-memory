import os
import subprocess
import tempfile
import json
import time
import hashlib
import ast
from deterministic_rng import set_seed, derive_seed
from grammar_engine import random_genome, mutate, crossover, build_ast
from vector_index import VectorIndex
from sandbox_basic import run_isolated

ENV_DIR = "prod_env"
RESULT_FILE = "archive.json"
POP_SIZE = 8
GENERATIONS = 5

def ensure_env():
    if not os.path.exists(ENV_DIR):
        subprocess.run("python3 -m venv prod_env", shell=True)
        subprocess.run(
            "prod_env/bin/pip install flask fastapi requests uvicorn psutil",
            shell=True
        )

def execute_module(module):
    source = ast.unparse(module)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(source)
        path = f.name
    result = run_isolated(f"{ENV_DIR}/bin/python {path}")
    return result.returncode, result.stdout.decode()

def fitness(rc, output):
    score = 0
    if rc == 0: score += 5
    if "error" not in output: score += 2
    score += len(output)*0.001
    return score

def main():
    ensure_env()
    index = VectorIndex()
    archive = []

    population = [random_genome() for _ in range(POP_SIZE)]

    for gen in range(GENERATIONS):
        print(f"=== Generation {gen} ===")
        scored = []

        for i, genome in enumerate(population):
            set_seed(derive_seed(gen,i))
            module = build_ast(genome)
            rc, out = execute_module(module)
            score = fitness(rc, out)
            vec = [sum(genome.values()), len(out)]

            scored.append((score, genome, vec, module))
            print(genome, score)

        scored.sort(reverse=True, key=lambda x: x[0])
        elites = scored[:POP_SIZE//2]

        for s in elites:
            archive.append({
                "score": s[0],
                "genome": s[1],
                "vector": s[2],
                "hash": hashlib.sha256(ast.unparse(s[3]).encode()).hexdigest()
            })
            index.add(s[2], s[1])

        next_pop = []
        while len(next_pop) < POP_SIZE:
            p1 = elites[0][1]
            p2 = elites[1][1]
            child = crossover(p1,p2)
            child = mutate(child)
            next_pop.append(child)

        population = next_pop

    with open(RESULT_FILE,"w") as f:
        json.dump(archive,f,indent=2)

    print("Evolution complete.")

if __name__ == "__main__":
    main()
