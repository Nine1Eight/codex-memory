#!/usr/bin/env python3
import numpy as np
from vil_real_encoder import get_vil

ALPHA = 0.60
BETA = 0.40

def cosine_sim(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / ((np.linalg.norm(a) + 1e-8) * (np.linalg.norm(b) + 1e-8)))

def text_to_glyph_ids(text):
    return [(ord(c) % 111) for c in text][:128] or [0]

def tokens_to_glyph_ids(tokens):
    return [(int(t) % 111) for t in tokens][:128] or [0]

def vil_score(input_text, tokens, base_score):
    vil = get_vil()
    input_vec = vil.encode(text_to_glyph_ids(input_text))
    output_vec = vil.encode(tokens_to_glyph_ids(tokens))

    sim = cosine_sim(input_vec, output_vec)
    sim_score = (sim + 1.0) / 2.0
    final = ALPHA * float(base_score) + BETA * sim_score * 10.0

    return {
        "base_score": float(base_score),
        "vil_similarity": float(sim),
        "vil_score": float(sim_score),
        "final_score": float(final)
    }
