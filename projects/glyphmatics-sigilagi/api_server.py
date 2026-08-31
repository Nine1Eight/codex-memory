from fastapi import FastAPI
from pydantic import BaseModel
from sigillm_numpy import *
from glyph_semantic_bridge import *
import uvicorn

app = FastAPI()

tok = GlyphTokenizer()
ds = load_dataset(tok)
model = NGramSigilLM()
model.fit(ds, epochs=5)

class Request(BaseModel):
    text: str
    mode: str = "balanced"

@app.post("/generate")
def generate(req: Request):
    target = target_profile(req.mode)
    seed = vector_to_seed(req.text, START, 8)
    tokens = model.generate(seed, target_roles=target["roles"])
    return {
        "input": req.text,
        "tokens": tokens,
        "glyphs": tok.decode(tokens),
        "meta": score(tokens, target)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
