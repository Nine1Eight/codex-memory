from sigillm_numpy import *
from glyph_semantic_bridge import *

tok = GlyphTokenizer()
model = NGramSigilLM()
model.fit(load_dataset(tok), epochs=5)

def predict(text):
    seed = vector_to_seed(text, START, 8)
    tokens = model.generate(seed)
    return tok.decode(tokens)
