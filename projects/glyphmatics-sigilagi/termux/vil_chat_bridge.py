#!/usr/bin/env python3
from glyph_semantic_bridge import vector_to_seed as hash_seed
from glyph_trainable_embedding import embedding_model
from vil_embedding_adapter import vil_adapter

def make_seed(text, backend="trainable", start=4094, n=8):
    backend = backend.lower().strip()

    if backend == "hash":
        return hash_seed(text, start, n)

    if backend == "vil":
        return vil_adapter.vector_to_seed(text, start=start, n=max(n, 12))

    return embedding_model.vector_to_seed(text, start=start, n=n)

def update_backend(text, backend, reward):
    if backend == "vil":
        vil_adapter.update(text, reward=reward)
        vil_adapter.save()
    elif backend == "trainable":
        embedding_model.update(text, reward=reward)
        embedding_model.save()
