#!/usr/bin/env python3
import random
from canon_engine_v4 import CVM

VALID_OPS = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF]

MAX_PROGRAM_LEN = 12


def random_program():
    program = []
    while len(program) < MAX_PROGRAM_LEN:
        op = random.choice(VALID_OPS)

        if op == 0x01:  # PUSH requires next byte
            program.append(op)
            program.append(random.randint(0, 255))
        else:
            program.append(op)

        if op == 0xFF:
            break

    if program[-1] != 0xFF:
        program.append(0xFF)

    return bytes(program)


def safe_execute(program):
    vm = CVM()
    try:
        vm.run(program)
        return True, vm.stack
    except:
        return False, []


def fitness(program):
    valid, stack = safe_execute(program)
    if not valid:
        return -1

    score = len(stack)
    score += sum(stack) * 0.01
    return score


def mutate(program):
    data = bytearray(program)

    i = random.randint(0, len(data)-1)

    if data[i] == 0x01 and i+1 < len(data):
        data[i+1] = random.randint(0, 255)
    else:
        data[i] = random.choice(VALID_OPS)

    return bytes(data)


def mine(iterations=500):
    best_prog = random_program()
    best_score = fitness(best_prog)

    print("Initial Score:", best_score)

    for i in range(iterations):
        candidate = mutate(best_prog)
        score = fitness(candidate)

        if score > best_score:
            best_score = score
            best_prog = candidate
            print(f"[{i}] New Best Score:", best_score)

    print("\nBest Program:", best_prog)
    print("Final Score:", best_score)


if __name__ == "__main__":
    mine()
