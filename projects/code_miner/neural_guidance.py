import random

class AdaptiveMutator:
    def __init__(self, genes):
        self.genes = genes
        self.weights = {g: 1.0 for g in genes}

    def update(self, genome, fitness):
        for g in self.genes:
            if genome[g]:
                self.weights[g] += fitness * 0.01

    def mutate(self, genome):
        g = genome.copy()
        gene = random.choices(
            self.genes,
            weights=[self.weights[k] for k in self.genes]
        )[0]
        g[gene] = not g[gene]
        return g
