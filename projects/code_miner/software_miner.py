#!/usr/bin/env python3
import random
import hashlib
from canon_engine_v4 import CVM

MAX_PROGRAM_LEN = 16


def random_program():
    length = random.randint(4, MAX_PROGRAM_LEN)
    return bytes(random.randint(0, 255) for _ in range(length))


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

    # Example fitness:
    # Reward deeper stack + nonzero values
    score = len(stack)
    score += sum(stack) * 0.01
    return score


def mutate(program):
    data = bytearray(program)
    i = random.randint(0, len(data)-1)
    data[i] = random.randint(0, 255)
    return bytes(data)


def mine(iterations=500):
    best_prog = random_program()
    best_score = fitness(best_prog)

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
