from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.submission.adapter import SubmissionAdapter, SubmissionError


class SubmissionTests(unittest.TestCase):
    def test_missing_official_schema_is_explicit(self) -> None:
        with self.assertRaisesRegex(SubmissionError, "unavailable"):
            SubmissionAdapter(Path("schemas/official-not-supplied.json"))

    def test_non_replayable_and_duplicate_rejected(self) -> None:
        schema = {
            "type": "object",
            "required": ["finding"],
            "properties": {"finding": {"type": "string"}},
            "additionalProperties": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "official.json"
            path.write_text(json.dumps(schema))
            adapter = SubmissionAdapter(path)
            with self.assertRaisesRegex(SubmissionError, "non-replayable"):
                adapter.build({"finding": "synthetic"}, False)
            with self.assertRaisesRegex(SubmissionError, "duplicate"):
                adapter.build({"finding": "synthetic"}, True, duplicate=True)

    def test_nested_schema_constraints_are_enforced(self) -> None:
        schema = {
            "type": "object",
            "required": ["finding", "scores"],
            "properties": {
                "finding": {"type": "string", "minLength": 3, "pattern": "^syn"},
                "scores": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 2,
                    "items": {"type": "integer", "minimum": 0, "maximum": 10},
                },
            },
            "additionalProperties": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "official.json"
            path.write_text(json.dumps(schema))
            adapter = SubmissionAdapter(path)
            with self.assertRaisesRegex(SubmissionError, "pattern"):
                adapter.validate({"finding": "bad", "scores": [1]})
            with self.assertRaisesRegex(SubmissionError, "maximum value"):
                adapter.validate({"finding": "synthetic", "scores": [11]})
            adapter.validate({"finding": "synthetic", "scores": [1, 2]})
