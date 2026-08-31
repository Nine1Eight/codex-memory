from sigillm_numpy import load_dataset, GlyphTokenizer
from sigil_neural_model import NeuralGlyphModel

tok = GlyphTokenizer()
ds = load_dataset(tok)

model = NeuralGlyphModel()

print("[TRAINING NEURAL GLYPH MODEL]")
model.train(ds, epochs=5)

model.save()
print("[SAVED neural_model.npz]")
