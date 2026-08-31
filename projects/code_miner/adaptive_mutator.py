import random
import hashlib

class AdaptiveMutator:
    def __init__(self, genes):
        self.genes = genes
        self.weights = {g: 1.0 for g in genes}

    def update(self, genome, fitness):
        # Simple reinforcement: increase weight of active genes
        for g in genome:
            if genome[g]:
                self.weights[g] += fitness * 0.01

        # Normalize weights
        total = sum(self.weights.values())
        for g in self.weights:
            self.weights[g] /= total

    def mutate(self, genome):
        g = genome.copy()

        # Weighted random gene selection
        gene = random.choices(
            population=self.genes,
            weights=[self.weights[k] for k in self.genes]
        )[0]

        g[gene] = not g[gene]
        return g
