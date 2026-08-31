import random
import json
import math
from multiprocessing import Pool
from grammar_engine import random_genome, crossover
from agent_worker import run_agent
from adaptive_mutator import AdaptiveMutator

POP_SIZE = 6
GENERATIONS = 6
WORKERS = 2
ARCHIVE_FILE = "archive.json"

# ------------------------------
# Dominance based on coordinates
# ------------------------------

def extract_vector(candidate):
    c = candidate["coordinates"]
    return [
        c["returncode"] == 0,
        -c["duration"],          # faster is better
        c["node_count"],
        -c["depth"]
    ]

def dominates(a, b):
    va = extract_vector(a)
    vb = extract_vector(b)

    better_or_equal = all(x >= y for x, y in zip(va, vb))
    strictly_better = any(x > y for x, y in zip(va, vb))
    return better_or_equal and strictly_better

def pareto_front(pop):
    front = []
    for candidate in pop:
        dominated = False
        for other in pop:
            if dominates(other, candidate):
                dominated = True
                break
        if not dominated:
            front.append(candidate)
    return front

# ------------------------------

def evolve_population(population, mutator, archive):
    with Pool(WORKERS) as pool:
        results = pool.map(run_agent, population)

    front = pareto_front(results)

    elites = front[:POP_SIZE // 2]

    next_population = []

    while len(next_population) < POP_SIZE:
        p1 = random.choice(elites)["genome"]
        p2 = random.choice(elites)["genome"]
        child = crossover(p1, p2)
        child = mutator.mutate(child)
        next_population.append(child)

    return next_population, elites

def main():
    population = [random_genome() for _ in range(POP_SIZE)]
    mutator = AdaptiveMutator(list(population[0].keys()))
    archive = []

    for gen in range(GENERATIONS):
        print(f"\n=== Generation {gen} ===")
        population, elites = evolve_population(population, mutator, archive)

        for e in elites:
            print(e)
            archive.append(e)

    with open(ARCHIVE_FILE, "w") as f:
        json.dump(archive, f, indent=2)

    print("\nAutonomous coordinate evolution complete.")

if __name__ == "__main__":
    main()
