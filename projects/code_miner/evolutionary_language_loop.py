#!/usr/bin/env python3
import random
from collections import Counter
from canon_engine_v4 import CVM

TARGET = 42
POP_SIZE = 80
MAX_BLOCKS = 6

LIBRARY = {}
LIB_COUNTER = 0

PRIMITIVES = [
    "PUSH_CONST",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "PRINT"
]


# =========================================================
# Compiler
# =========================================================

def compile_program(blocks):
    bytecode = []

    for block in blocks:

        if block[0].startswith("LIB_"):
            for sub in LIBRARY[block[0]]:
                bytecode.extend(compile_program([sub]))
            continue

        if block[0] == "PUSH_CONST":
            bytecode.append(0x01)
            bytecode.append(block[1])
        elif block[0] == "ADD":
            bytecode.append(0x02)
        elif block[0] == "SUB":
            bytecode.append(0x03)
        elif block[0] == "MUL":
            bytecode.append(0x04)
        elif block[0] == "DIV":
            bytecode.append(0x05)
        elif block[0] == "PRINT":
            bytecode.append(0x06)

    bytecode.append(0xFF)
    return bytes(bytecode)


# =========================================================
# Evaluation
# =========================================================

def evaluate(blocks):
    bytecode = compile_program(blocks)
    vm = CVM()

    stack = []
    pc = 0
    arith = 0
    output = None

    try:
        while pc < len(bytecode):
            op = bytecode[pc]
            pc += 1

            if op == 0x01:
                val = bytecode[pc]
                pc += 1
                stack.append(val)

            elif op in [0x02, 0x03, 0x04, 0x05]:
                arith += 1
                b = stack.pop()
                a = stack.pop()
                if op == 0x02:
                    stack.append((a + b) & 0xFF)
                elif op == 0x03:
                    stack.append((a - b) & 0xFF)
                elif op == 0x04:
                    stack.append((a * b) & 0xFF)
                elif op == 0x05:
                    if b == 0:
                        return -1000
                    stack.append((a // b) & 0xFF)

            elif op == 0x06:
                output = stack.pop()

            elif op == 0xFF:
                break

        if output is None:
            return -1000

        goal_score = -abs(output - TARGET) * 5
        arith_bonus = arith * 4
        length_penalty = len(blocks) * 0.5

        return goal_score + arith_bonus - length_penalty

    except:
        return -1000


# =========================================================
# Genetic Operators
# =========================================================

def random_program():
    blocks = []
    for _ in range(random.randint(3, MAX_BLOCKS)):
        prim = random.choice(PRIMITIVES + list(LIBRARY.keys()))
        if prim == "PUSH_CONST":
            blocks.append(("PUSH_CONST", random.randint(0, 20)))
        else:
            blocks.append((prim,))
    return blocks


def mutate(blocks):
    new_blocks = blocks.copy()
    i = random.randint(0, len(new_blocks)-1)

    prim = random.choice(PRIMITIVES + list(LIBRARY.keys()))
    if prim == "PUSH_CONST":
        new_blocks[i] = ("PUSH_CONST", random.randint(0, 20))
    else:
        new_blocks[i] = (prim,)

    return new_blocks


def crossover(a, b):
    if len(a) < 2 or len(b) < 2:
        return a

    cut_a = random.randint(1, len(a)-1)
    cut_b = random.randint(1, len(b)-1)

    child = a[:cut_a] + b[cut_b:]
    return child[:MAX_BLOCKS]


# =========================================================
# Library Abstraction
# =========================================================

def abstract_library(elites):
    global LIB_COUNTER

    subseq_counter = Counter()

    for prog in elites:
        for i in range(len(prog)-2):
            subseq = tuple(prog[i:i+3])
            subseq_counter[subseq] += 1

    most_common = subseq_counter.most_common(1)
    if not most_common:
        return

    subseq, count = most_common[0]

    if count > 10:
        name = f"LIB_{LIB_COUNTER}"
        LIB_COUNTER += 1
        LIBRARY[name] = list(subseq)
        print(">> New Library Primitive:", name, "=", subseq)


# =========================================================
# Continuous Evolution Loop
# =========================================================

def run_forever():
    generation_global = 0
    population = [random_program() for _ in range(POP_SIZE)]

    while True:

        scored = [(evaluate(p), p) for p in population]
        scored.sort(reverse=True, key=lambda x: x[0])

        best_score, best_prog = scored[0]

        if generation_global % 50 == 0:
            print(f"[Gen {generation_global}] Best Score:", best_score)
            print("Library Size:", len(LIBRARY))

        elites = [p for (_, p) in scored[:20]]

        if generation_global % 200 == 0 and generation_global > 0:
            abstract_library(elites)

        new_population = elites.copy()

        while len(new_population) < POP_SIZE:
            if random.random() < 0.5:
                parent = random.choice(elites)
                child = mutate(parent)
            else:
                p1, p2 = random.sample(elites, 2)
                child = crossover(p1, p2)

            new_population.append(child)

        population = new_population
        generation_global += 1


if __name__ == "__main__":
    run_forever()
