import unittest
import tempfile
from pathlib import Path

import glyph_grid as gm


class GlyphGridTests(unittest.TestCase):
    def test_grid_assigns_every_command_once(self):
        assigned = [value for row in gm.grid() for value in row if value is not None]
        self.assertEqual(assigned, list(range(333)))

    def test_pair_round_trip(self):
        for pair in ((0, 0), (30, 32), (332, 332)):
            self.assertEqual(gm.unpack_pair(gm.pack_pair(*pair)), pair)

    def test_delta_round_trip(self):
        sequence = [30, 2, 37, 2, 32, 72, 2, 2, 0]
        self.assertEqual(gm.delta_decode(gm.delta_encode(sequence)), sequence)

    def test_execution_edges_are_directed_and_ordered(self):
        edges = gm.execution_edges([30, 37, 32, 0])
        self.assertEqual([(e["from"], e["to"]) for e in edges],
                         [(30, 37), (37, 32), (32, 0)])

    def test_repeat_encoding(self):
        self.assertEqual(gm.run_length_encode([2, 2, 2, 0]),
                         [{"command": 2, "times": 3}, {"command": 0, "times": 1}])

    def test_svg_container_round_trip(self):
        sequence = [30, 2, 37, 2, 32, 72, 2, 2, 0]
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "program.svg"
            image.write_text(gm.render_svg(sequence), encoding="utf-8")
            self.assertEqual(gm.decode_svg(image), sequence)

    def test_llm_weight_colors_are_distinct(self):
        colors = {gm.node(command).color for command in (200, 201, 202, 207, 211)}
        self.assertEqual(len(colors), 5)

    def test_llm_execution_has_fixed_grid_location(self):
        operation = gm.node(160)
        self.assertEqual((operation.row, operation.column), divmod(160, gm.COLS))
        self.assertEqual(operation.kind, "llm_execution")


if __name__ == "__main__":
    unittest.main()
