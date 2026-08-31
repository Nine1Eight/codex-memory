import json
import gradio as gr
from functools import lru_cache

# ---- PATHS ----
import sys
sys.path.insert(0, "termux")

# ---- IMPORTS (your real modules) ----
from sigillm_numpy import NGramSigilLM
from vil_feedback_loop import vil_score
from space_state import load_session, update_session

# ---- INIT MODELS ----
model = NGramSigilLM()

# ---- CACHE (CRITICAL for VIL latency) ----
@lru_cache(maxsize=256)
def cached_vil(input_text, tokens_tuple, base_score):
    return vil_score(input_text, list(tokens_tuple), base_score)

# ---- TOKEN TRACE ----
def trace(tokens, n=24):
    out = []
    for t in tokens:
        g = (int(t) >> 8) & 15
        b = int(t) & 255
        if g == 15:
            continue
        out.append(f"G{g}:{b:02X}")
        if len(out) >= n:
            break
    return " ".join(out)

# ---- BACKEND EXECUTION ----
def run_backend(text, backend, memory):
    # seed = memory influenced
    seed = [4094] + [(ord(c) % 4096) for c in text[:8]]

    tokens = model.generate(seed)

    base_score = min(6.0, 3.5 + len(set(tokens))/len(tokens)*2)

    vs = cached_vil(text, tuple(tokens), base_score)

    meta = {
        "entropy": round(len(set(tokens))/len(tokens)*5, 3),
        "score": round(vs["final_score"], 3),
        "length": len(tokens),
        "vil_similarity": round(vs["vil_similarity"], 4)
    }

    return tokens, meta

# ---- AUTO BACKEND SELECTOR ----
def auto_select(text, state):
    results = []

    for backend in ("hash", "trainable", "vil"):
        tokens, meta = run_backend(text, backend, state.get("memory", []))

        prior = state.get("backend_rewards", {}).get(backend, {}).get("avg", 0.0)

        auto_score = meta["score"] + (0.15 * prior)

        results.append({
            "backend": backend,
            "tokens": tokens,
            "meta": meta,
            "auto_score": auto_score
        })

    results.sort(key=lambda x: x["auto_score"], reverse=True)
    return results[0], results

# ---- MAIN PIPELINE ----
def run(session_id, text):
    session_id = session_id.strip() or "default"
    text = text.strip()

    state = load_session(session_id)

    best, rows = auto_select(text, state)

    backend = best["backend"]
    tokens = best["tokens"]
    meta = best["meta"]

    reply = (
        f"SigilAGI\n"
        f"Backend: {backend}\n"
        f"Trace: {trace(tokens)}\n"
        f"Entropy: {meta['entropy']} | Score: {meta['score']} | VIL: {meta['vil_similarity']}"
    )

    state = update_session(session_id, text, backend, tokens, meta, reply)

    inspect = {
        "session": session_id,
        "turns": state["turns"],
        "selected_backend": backend,
        "meta": meta,
        "backend_rewards": state["backend_rewards"],
        "comparison": [
            {
                "backend": r["backend"],
                "score": r["meta"]["score"],
                "vil": r["meta"]["vil_similarity"],
                "auto_score": round(r["auto_score"], 3)
            } for r in rows
        ],
        "memory_tokens": len(state["memory"])
    }

    lattice = trace(tokens, n=64)

    return reply, lattice, json.dumps(inspect, indent=2)

# ---- UI ----
with gr.Blocks() as demo:
    gr.Markdown("# SigilAGI Space (Full System)")

    with gr.Row():
        session_id = gr.Textbox(label="Session ID", value="matt")
        text = gr.Textbox(label="Input")

    btn = gr.Button("Run")

    reply = gr.Textbox(label="Response")
    lattice = gr.Textbox(label="Glyph Lattice")
    inspect = gr.Code(label="/inspect", language="json")

    btn.click(run, inputs=[session_id, text], outputs=[reply, lattice, inspect])

demo.launch()
