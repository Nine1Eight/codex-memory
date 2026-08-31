#!/usr/bin/env python3
import random
from canon_engine_v4 import CVM

VALID_OPS = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF]
ARITH_OPS = [0x02, 0x03, 0x04, 0x05]

TARGET = 42
MIN_ARITH = 3
MAX_LEN = 14
POP_SIZE = 80


def random_program():
    program = []
    while len(program) < MAX_LEN:
        op = random.choice(VALID_OPS)

        if op == 0x01:
            program.append(op)
            program.append(random.randint(0, 20))
        else:
            program.append(op)

        if op == 0xFF:
            break

    if program[-1] != 0xFF:
        program.append(0xFF)

    return bytes(program)


def analyze(program):
    vm = CVM()
    stack = []
    pc = 0
    arith = 0
    nops = 0
    output = None

    try:
        while pc < len(program):
            op = program[pc]
            pc += 1

            if op == 0x00:
                nops += 1
                continue

            elif op == 0x01:
                val = program[pc]
                pc += 1
                stack.append(val)

            elif op in ARITH_OPS:
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
                        return False, None, 0, 0
                    stack.append((a // b) & 0xFF)

            elif op == 0x06:
                output = stack.pop()

            elif op == 0xFF:
                break

        return True, output, arith, nops

    except:
        return False, None, 0, 0


def fitness(program):
    valid, output, arith, nops = analyze(program)

    if not valid or output is None:
        return -1000

    goal_score = -abs(output - TARGET) * 5
    arith_requirement = 20 if arith >= MIN_ARITH else -20
    depth_score = arith * 4
    length_penalty = len(program) * 0.5
    nop_penalty = nops * 1.5

    return (
        goal_score +
        arith_requirement +
        depth_score -
        length_penalty -
        nop_penalty
    )


def mutate(program):
    data = bytearray(program)
    i = random.randint(0, len(data)-1)

    if data[i] == 0x01 and i+1 < len(data):
        data[i+1] = random.randint(0, 20)
    else:
        data[i] = random.choice(VALID_OPS)

    return bytes(data)


def evolve(generations=4000):
    population = [random_program() for _ in range(POP_SIZE)]

    for gen in range(generations):
        scored = [(fitness(p), p) for p in population]
        scored.sort(reverse=True, key=lambda x: x[0])

        best_score, best_prog = scored[0]

        if gen % 100 == 0:
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
