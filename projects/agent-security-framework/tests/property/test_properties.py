from __future__ import annotations

import random
import unittest

from src.generators.mutations import MutationGenerator
from src.models.canonical import canonical_json, stable_hash


class PropertyTests(unittest.TestCase):
    def test_canonical_serialization_is_deterministic_for_many_orders(self) -> None:
        rng = random.Random(918)
        pairs = [(str(i), i) for i in range(50)]
        expected = stable_hash(dict(pairs))
        for _ in range(100):
            rng.shuffle(pairs)
            self.assertEqual(stable_hash(dict(pairs)), expected)

    def test_mutations_reproduce_from_seed(self) -> None:
        for seed in range(50):
            left = MutationGenerator(seed).generate({"value": seed})
            right = MutationGenerator(seed).generate({"value": seed})
            self.assertEqual(canonical_json(left), canonical_json(right))
            self.assertTrue(all(candidate.trust == "untrusted" for candidate in left))
