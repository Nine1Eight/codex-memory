import random
from ledger import (
    init_ledger,
    register_genome,
    update_stake,
    transfer,
    purge_bankrupt,
    emission_for_generation
)
from species_rewards import (
    builder_reward,
    attacker_reward,
    optimizer_reward
)

GENERATION_LIMIT = 20

def simulate_builder(genome):
    return {
        "functionality": random.randint(0, 20),
        "stability": random.randint(0, 10)
    }

def simulate_attacker(builder_hash):
    success = random.random() < 0.3
    return success

def simulate_optimizer(builder_scores):
    runtime_gain = random.uniform(0, 2)
    ast_gain = random.uniform(0, 1)
    retention = random.uniform(0.8, 1.0)
    return runtime_gain, ast_gain, retention

def main():
    init_ledger()

    builders = []
    attackers = []
    optimizers = []

    for i in range(5):
        h = f"builder_{i}"
        register_genome(h, "builder")
        builders.append(h)

    for i in range(3):
        h = f"attacker_{i}"
        register_genome(h, "attacker")
        attackers.append(h)

    for i in range(3):
        h = f"optimizer_{i}"
        register_genome(h, "optimizer")
        optimizers.append(h)

    for gen in range(GENERATION_LIMIT):
        emission = emission_for_generation(gen)

        for b in builders:
            scores = simulate_builder(b)
            runtime_gain, ast_gain, retention = simulate_optimizer(scores)

            reward = builder_reward(scores, 1, retention, 0.5)
            update_stake(b, reward)

            for a in attackers:
                if simulate_attacker(b):
                    transfer(b, a, 2.0, "exploit")

        for o in optimizers:
            reward = optimizer_reward(
                random.uniform(0, 2),
                random.uniform(0, 1),
                random.uniform(0.8, 1.0)
            )
            update_stake(o, reward)

        purge_bankrupt()
        print(f"Generation {gen} complete.")

    print("Distributed ecological economy complete.")

if __name__ == "__main__":
    main()
