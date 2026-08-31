#!/usr/bin/env python3
import random
from canon_engine_v4 import CVM

VALID_OPS = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xFF]
ARITH_OPS = [0x02, 0x03, 0x04, 0x05]

TARGET = 42
MAX_LEN = 16


def random_program():
    program = []
    while len(program) < MAX_LEN:
        op = random.choice(VALID_OPS)

        if op == 0x01:  # PUSH
            program.append(op)
            program.append(random.randint(0, 20))  # small values for search stability
        else:
            program.append(op)

        if op == 0xFF:
            break

    if program[-1] != 0xFF:
        program.append(0xFF)

    return bytes(program)


def safe_execute(program):
    vm = CVM()
    output = None
    arith_count = 0

    pc = 0
    stack = []
    try:
        while pc < len(program):
            op = program[pc]
            pc += 1

            if op == 0x00:
                continue

            elif op == 0x01:
                val = program[pc]
                pc += 1
                stack.append(val)

            elif op in ARITH_OPS:
                arith_count += 1
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
                        return False, None, 0
                    stack.append((a // b) & 0xFF)

            elif op == 0x06:
                output = stack.pop()

            elif op == 0xFF:
                break

            else:
                return False, None, 0

        return True, output, arith_count

    except:
        return False, None, 0


def fitness(program):
    valid, output, arith = safe_execute(program)
    if not valid or output is None:
        return -1000

    goal_score = -abs(output - TARGET)
    depth_score = arith * 2
    length_penalty = len(program) * 0.2

    return goal_score + depth_score - length_penalty


def mutate(program):
    data = bytearray(program)

    i = random.randint(0, len(data)-1)

    if data[i] == 0x01 and i+1 < len(data):
        data[i+1] = random.randint(0, 20)
    else:
        data[i] = random.choice(VALID_OPS)

    return bytes(data)


def mine(iterations=2000):
    best = random_program()
    best_score = fitness(best)

    print("Initial Score:", best_score)

    for i in range(iterations):
        candidate = mutate(best)
        score = fitness(candidate)

        if score > best_score:
            best_score = score
            best = candidate
            print(f"[{i}] Score:", best_score, "Program:", best)

        if best_score >= 0:
            break

    print("\nFinal Best Program:", best)
    print("Final Score:", best_score)


if __name__ == "__main__":
    mine()
