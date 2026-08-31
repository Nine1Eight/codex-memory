import numpy as np

class VectorIndex:
    def __init__(self):
        self.vectors = []
        self.meta = []

    def add(self, vec, metadata):
        self.vectors.append(np.array(vec))
        self.meta.append(metadata)

    def search(self, query, top_k=3):
        q = np.array(query)
        sims = [
            (i, np.dot(q, v) / (np.linalg.norm(q)*np.linalg.norm(v)+1e-9))
            for i, v in enumerate(self.vectors)
        ]
        sims.sort(key=lambda x: x[1], reverse=True)
        return [self.meta[i] for i,_ in sims[:top_k]]
