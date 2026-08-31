"""
Feature‑engineering pipeline for large‑language‑model embeddings.

This module implements a configurable pipeline that transforms raw
embedding vectors into enriched feature representations.  It follows
the seven stages described in the system definition【527482634550503†L17-L35】:

1. **Semantic similarity & anchors** – Compute similarity scores against
   a set of anchor vectors.
2. **Clustering & structure** – Cluster embeddings and assign a
   categorical cluster ID.
3. **Pairwise interaction features** – Combine similarity features
   pairwise to capture interactions.
4. **Dimensionality reduction & denoising** – Reduce the dimensionality
   of embeddings using PCA.
5. **Embedding normalization** – L2‑normalize the original embeddings.
6. **Aggregation** – Aggregate multiple embeddings into a single
   representation (mean and variance).
7. **Feature synthesis** – Placeholder for synthetic features derived
   from machine‑learning models (currently unimplemented).

The pipeline returns a dictionary of numpy arrays or scalar values for
each embedding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize


def _cosine_similarity(x: np.ndarray, y: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    # Ensure both are 1D
    x = x.reshape(-1)
    y = y.reshape(-1)
    # Avoid division by zero
    x_norm = np.linalg.norm(x)
    y_norm = np.linalg.norm(y)
    if x_norm == 0 or y_norm == 0:
        return 0.0
    return float(np.dot(x, y) / (x_norm * y_norm))


@dataclass
class EmbeddingFeatureEngineer:
    """Transforms raw embeddings into enriched feature vectors."""

    n_clusters: int = 5
    n_components: int = 5
    include_pairwise: bool = True

    _kmeans: Optional[KMeans] = field(default=None, init=False, repr=False)
    _pca: Optional[PCA] = field(default=None, init=False, repr=False)

    def _fit_clustering(self, embeddings: List[np.ndarray]) -> None:
        """Fit a KMeans model on the embeddings if not already fitted."""
        if self._kmeans is None:
            # Stack embeddings into matrix
            X = np.stack(embeddings, axis=0)
            self._kmeans = KMeans(n_clusters=self.n_clusters, random_state=0, n_init="auto")
            self._kmeans.fit(X)

    def _fit_pca(self, embeddings: List[np.ndarray]) -> None:
        """Fit a PCA model on the embeddings if not already fitted."""
        if self._pca is None:
            X = np.stack(embeddings, axis=0)
            self._pca = PCA(n_components=min(self.n_components, X.shape[1]), random_state=0)
            self._pca.fit(X)

    def transform(self, embeddings: Sequence[np.ndarray], anchor_vectors: Sequence[np.ndarray]) -> List[dict]:
        """
        Transform a list of embedding vectors into enriched feature representations.

        Parameters
        ----------
        embeddings : Sequence[np.ndarray]
            List of embedding vectors to transform (each of shape `(dim,)`).
        anchor_vectors : Sequence[np.ndarray]
            List of anchor vectors used for similarity calculations.

        Returns
        -------
        List[dict]
            A list of dictionaries, one per input embedding, containing the
            engineered features.
        """
        # Ensure we have models fitted
        self._fit_clustering(list(embeddings))
        self._fit_pca(list(embeddings))
        results: List[dict] = []
        # Precompute aggregated features across dataset
        aggregated_mean = np.mean(np.stack(embeddings, axis=0), axis=0)
        aggregated_var = np.var(np.stack(embeddings, axis=0), axis=0)
        for emb in embeddings:
            feature_dict: dict = {}
            # 1. Similarity to anchors
            similarities = np.array([
                _cosine_similarity(emb, anchor) for anchor in anchor_vectors
            ], dtype=np.float32)
            feature_dict["similarities"] = similarities
            # 2. Cluster assignment
            cluster_id = int(self._kmeans.predict(emb.reshape(1, -1))[0])
            feature_dict["cluster_id"] = cluster_id
            # 3. Pairwise interaction features
            if self.include_pairwise:
                # Compute all unique pairs of similarity scores
                pairwise = []
                for i in range(len(similarities)):
                    for j in range(i + 1, len(similarities)):
                        pairwise.append(similarities[i] * similarities[j])
                feature_dict["pairwise"] = np.array(pairwise, dtype=np.float32)
            # 4. Dimensionality reduction (PCA)
            pca_vec = self._pca.transform(emb.reshape(1, -1)).reshape(-1).astype(np.float32)
            feature_dict["pca"] = pca_vec
            # 5. Normalized embedding
            norm_emb = normalize(emb.reshape(1, -1), norm="l2")[0].astype(np.float32)
            feature_dict["normalized"] = norm_emb
            # 6. Aggregation: include mean and variance of all embeddings
            # These aggregated features are the same for every record; they
            # provide global context.
            feature_dict["aggregated_mean"] = aggregated_mean.astype(np.float32)
            feature_dict["aggregated_var"] = aggregated_var.astype(np.float32)
            # 7. Synthetic features (placeholder)
            # A real implementation could train a model (e.g., RandomForest)
            # to predict anchor similarities or other targets.
            feature_dict["synthetic"] = np.zeros((1,), dtype=np.float32)
            results.append(feature_dict)
        return results