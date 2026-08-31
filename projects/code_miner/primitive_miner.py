#!/usr/bin/env python3
import random
from canon_engine_v4 import CVM

TARGET = 42
POP_SIZE = 60
MAX_BLOCKS = 6

PRIMITIVES = [
    "PUSH_CONST",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "PRINT"
]


# ===============================
# Compiler
# ===============================

def compile_program(blocks):
    bytecode = []
    for block in blocks:
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


# ===============================
# Random Program
# ===============================

def random_program():
    blocks = []
    for _ in range(random.randint(3, MAX_BLOCKS)):
        prim = random.choice(PRIMITIVES)
        if prim == "PUSH_CONST":
            blocks.append(("PUSH_CONST", random.randint(0, 20)))
        else:
            blocks.append((prim,))
    return blocks


# ===============================
# Execution
# ===============================

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
        arith_bonus = arith * 3
        length_penalty = len(blocks) * 0.5

        return goal_score + arith_bonus - length_penalty

    except:
        return -1000


# ===============================
# Mutation
# ===============================

def mutate(blocks):
    new_blocks = blocks.copy()
    i = random.randint(0, len(new_blocks)-1)

    prim = random.choice(PRIMITIVES)

    if prim == "PUSH_CONST":
        new_blocks[i] = ("PUSH_CONST", random.randint(0, 20))
    else:
        new_blocks[i] = (prim,)

    return new_blocks


# ===============================
# Evolution
# ===============================

def evolve(generations=2000):
    population = [random_program() for _ in range(POP_SIZE)]

    for gen in range(generations):
        scored = [(evaluate(p), p) for p in population]
        scored.sort(reverse=True, key=lambda x: x[0])

        best_score, best_prog = scored[0]

        if gen % 50 == 0:
            print(f"[Gen {gen}] Best Score:", best_score)

        if best_score > 0:
            print("\nSolved at generation", gen)
            print("Program:", best_prog)
            print("Score:", best_score)
            return

        elites = [p for (_, p) in scored[:15]]

        new_population = elites.copy()
        while len(new_population) < POP_SIZE:
            parent = random.choice(elites)
            child = mutate(parent)
            new_population.append(child)

        population = new_population

    print("\nFinal Best:", best_prog)
    print("Final Score:", best_score)


if __name__ == "__main__":
    evolve()
