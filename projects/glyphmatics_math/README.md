# Glyphmatics Math command grid

This prototype assigns command IDs `000` through `332` to a stable 19-by-18
grid. The final nine cells are unused. Grid neighbors support spatial lookup;
program execution is represented separately by directed edges.

The completed grid image is the final container. It displays the participating
command cells and directed execution edges. Its SVG metadata carries the exact
numeric sequence and a SHA-256 checksum, allowing deterministic recovery
without OCR. The source-code screenshot is never stored.

Operators represented by commands `250` through `253`:

- `+`: ordered execution sequence
- `-`: signed delta from the preceding command number
- `x`: exact repetition of a command
- `/`: unpack a pair using quotient and remainder with base 333

Example command sequence for `def square(x): return x * x`:

```text
030,002,037,002,032,072,002,002,000
```

Generate its execution graph:

```sh
python glyph_grid.py trace '30,2,37,2,32,72,2,2,0'
```

Other commands:

```sh
python glyph_grid.py grid
python glyph_grid.py inspect 30
python glyph_grid.py render '30,2,37,2,32,72,2,2,0' square.svg
python glyph_grid.py decode-svg square.svg
```

The JSON trace includes explicit execution edges, delta encoding, repeated-run
encoding, and packed adjacent pairs. Packing is reversible representation, not
by itself a reduction in information.

## LLM grid assignments

- `150–189`: LLM execution steps (green)
- `200, 221`: embedding weights (blue)
- `201, 206, 210`: normalization weights (yellow)
- `202–205, 212–215, 220`: attention weights (purple)
- `207–209, 216–218`: MLP weights (orange)
- `211, 219`: output-head weights (red)

Weight nodes are references to tensors and do not imply that billions of tensor
values fit inside one command number. A model manifest must map each numbered
weight node to its tensor shape, data type, checksum, and payload location.
