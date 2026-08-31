#!/usr/bin/env python3
from collections import defaultdict
from pathlib import Path
import json
import sys
import time

from sigillm_numpy import (
    GlyphTokenizer,
    NGramSigilLM,
    load_dataset,
    score,
    target_profile,
    render_tokens_png,
    START,
)

from vil_chat_bridge import make_seed, update_backend
from glyph_trainable_embedding import embedding_model
from sigil_neural_model import NeuralGlyphModel
from auto_backend_patch import enhance_with_vil
from persistent_agent import (
    load_agent_state,
    save_agent_state,
    make_memory,
    make_backend_stats,
    persist_runtime,
    log_turn,
)

tok = GlyphTokenizer()

model = NGramSigilLM()
model.use_transformer = False
model.transformer = None

ds = load_dataset(tok)
model.fit(ds, epochs=10)

neural_model = NeuralGlyphModel()
neural_model.load()

AGENT_STATE = load_agent_state()

USE_NEURAL = False
CURRENT_TARGET = target_profile(AGENT_STATE["mode"]) if AGENT_STATE.get("mode") else None
CURRENT_MODE = AGENT_STATE.get("mode")
SEED_BACKEND = AGENT_STATE.get("last_backend", "trainable")
AUTO_BACKEND = bool(AGENT_STATE.get("auto_backend", False))
MEMORY = make_memory(maxlen=256)
BACKEND_STATS = make_backend_stats()


def safe_save():
    try:
        embedding_model.save()
    except Exception:
        pass

    try:
        persist_runtime(MEMORY, BACKEND_STATS, SEED_BACKEND, AUTO_BACKEND, CURRENT_MODE)
    except Exception:
        pass


def reward_backend(backend, meta, text):
    reward = float(meta.get("score", 0.0))

    if meta.get("valid", False):
        reward += 0.25

    reward += min(float(meta.get("entropy", 0.0)) / 4.0, 1.0) * 0.25

    st = BACKEND_STATS[backend]
    st["uses"] = int(st.get("uses", 0)) + 1
    st["reward"] = float(st.get("reward", 0.0)) + reward
    st["avg"] = st["reward"] / max(1, st["uses"])

    if reward > 4.5:
        update_backend(text, backend, reward=min(reward / 5.0, 2.0))

    safe_save()
    return reward


def parse_command(text):
    global CURRENT_TARGET, CURRENT_MODE, USE_NEURAL, SEED_BACKEND, AUTO_BACKEND

    if text.startswith("/mode"):
        mode = text.split(" ", 1)[-1].strip()
        CURRENT_MODE = mode
        CURRENT_TARGET = target_profile(mode)
        print("[MODE]", mode)
        safe_save()
        return True

    if text.startswith("/seed"):
        backend = text.split(" ", 1)[-1].strip().lower()
        if backend not in ("hash", "trainable", "vil"):
            print("[SEED ERROR] use: /seed hash | /seed trainable | /seed vil")
            return True

        SEED_BACKEND = backend
        AUTO_BACKEND = False
        print("[SEED]", SEED_BACKEND)
        safe_save()
        return True

    if text == "/auto on":
        AUTO_BACKEND = True
        print("[AUTO BACKEND ON]")
        safe_save()
        return True

    if text == "/auto off":
        AUTO_BACKEND = False
        print("[AUTO BACKEND OFF]")
        safe_save()
        return True

    if text == "/neural on":
        USE_NEURAL = True
        print("[NEURAL ON]")
        return True

    if text == "/neural off":
        USE_NEURAL = False
        print("[NEURAL OFF]")
        return True

    if text == "/clear":
        MEMORY.clear()
        print("[MEMORY CLEARED]")
        safe_save()
        return True

    if text == "/rewards":
        print(json.dumps(dict(BACKEND_STATS), indent=2))
        return True

    if text == "/status":
        print(json.dumps({
            "memory_size": len(MEMORY),
            "mode": CURRENT_MODE,
            "seed_backend": SEED_BACKEND,
            "auto_backend": AUTO_BACKEND,
            "neural": USE_NEURAL,
            "backend_stats": dict(BACKEND_STATS),
        }, indent=2))
        return True

    return False


def inject_memory(seed):
    if not MEMORY:
        return seed
    return seed + list(MEMORY)[-12:]


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


def generate(seed):
    if USE_NEURAL:
        tokens = list(seed)
        for _ in range(32):
            tokens.append(neural_model.next_token(tokens))
        return tokens

    return model.generate(seed)


def score_tokens(tokens):
    if CURRENT_TARGET:
        return score(tokens, CURRENT_TARGET)
    return score(tokens)


def run_backend(text, backend):
    seed = make_seed(text, backend=backend, start=START, n=8)
    seed = inject_memory(seed)
    tokens = generate(seed)
    meta = score_tokens(tokens)

    return {
        "backend": backend,
        "tokens": tokens,
        "meta": meta,
        "entropy": round(meta["entropy"], 3),
        "score": round(meta["score"], 3),
        "length": meta["length"],
        "trace": trace(tokens, n=12),
    }


def compare_backends(text, verbose=True):
    rows = [run_backend(text, b) for b in ("hash", "trainable", "vil")]
    rows.sort(key=lambda r: r["meta"]["score"], reverse=True)

    if verbose:
        print("[COMPARE]", text)
        for r in rows:
            print(
                f"{r['backend']:10s} "
                f"H={r['entropy']} "
                f"score={r['score']} "
                f"len={r['length']} "
                f"trace={r['trace']}"
            )

    return rows


def auto_select_backend(text):
    rows = compare_backends(text, verbose=False)
    rows = enhance_with_vil(text, rows)

    for r in rows:
        prior = BACKEND_STATS[r["backend"]].get("avg", 0.0)
        r["auto_score"] = float(r["final_score"]) + 0.10 * float(prior)

    rows.sort(key=lambda r: r["auto_score"], reverse=True)
    return rows[0], rows


def readable_reply(user, tokens, meta, backend):
    q = user.lower()

    if "who are you" in q:
        lead = "I am SigilAGI: a persistent glyph-native symbolic/neural agent with memory, reinforcement routing, and selectable semantic seed backends."
    elif any(x in q for x in ("hello", "hi", "hey")):
        lead = "Signal received."
    elif any(x in q for x in ("build", "make", "create", "write")):
        lead = "Execution path formed."
    elif any(x in q for x in ("why", "how", "what")):
        lead = "Decoded answer path formed."
    else:
        lead = "Glyph response generated."

    return (
        f"{lead}\n"
        f"Trace: {trace(tokens)}\n"
        f"Metrics: entropy={meta['entropy']:.3f}, "
        f"score={meta['score']:.3f}, "
        f"length={meta['length']}, "
        f"backend={backend}, "
        f"auto={AUTO_BACKEND}, "
        f"neural={USE_NEURAL}, "
        f"memory={len(MEMORY)}"
    )


def save_turn(user, reply, tokens, meta, backend, comparison=None):
    Path("chat_exports").mkdir(exist_ok=True)

    render_tokens_png(tokens, "chat_exports/latest_reply.png")

    Path("chat_exports/latest_reply.json").write_text(json.dumps({
        "time": time.time(),
        "user": user,
        "reply": reply,
        "backend": backend,
        "auto_backend": AUTO_BACKEND,
        "neural": USE_NEURAL,
        "memory_size": len(MEMORY),
        "tokens": tokens,
        "glyphs": tok.decode(tokens),
        "meta": meta,
        "comparison": comparison,
    }, indent=2))


def chat():
    global SEED_BACKEND

    print("[SIGIL CHAT READY]")
    print("Persistent agent active.")
    print("Commands: /mode <balanced|water|flow|transform>, /seed <hash|trainable|vil>, /auto on/off, /compare <text>, /rewards, /neural on/off, /clear, /status, exit")

    while True:
        try:
            user = input("\nYou> ").strip()
        except KeyboardInterrupt:
            print("\n[INTERRUPT] Saving state...")
            safe_save()
            sys.exit(0)

        if user.lower() in ("exit", "quit"):
            print("[EXIT] Saving state...")
            safe_save()
            sys.exit(0)

        if parse_command(user):
            continue

        if user.startswith("/compare "):
            compare_backends(user.split(" ", 1)[1].strip(), verbose=True)
            continue

        comparison = None

        if AUTO_BACKEND:
            best, rows = auto_select_backend(user)
            backend = best["backend"]
            tokens = best["tokens"]
            meta = best["meta"]
            comparison = [
                {
                    "backend": r["backend"],
                    "score": r["score"],
                    "entropy": r["entropy"],
                    "length": r["length"],
                    "auto_score": round(r["auto_score"], 3),
                    "vil_similarity": round(r.get("vil_similarity", 0.0), 4),
                    "final_score": round(r.get("final_score", r["score"]), 3),
                }
                for r in rows
            ]
            SEED_BACKEND = backend
            print("[AUTO SELECT]", backend)
        else:
            backend = SEED_BACKEND
            result = run_backend(user, backend)
            tokens = result["tokens"]
            meta = result["meta"]

        MEMORY.extend(tokens[-12:])

        reward = reward_backend(backend, meta, user)

        reply = readable_reply(user, tokens, meta, backend)
        save_turn(user, reply, tokens, meta, backend, comparison=comparison)
        log_turn(user, reply, backend, meta)

        print("SigilAGI>", reply)
        print("[REWARD]", round(reward, 3))
        print("[PNG] chat_exports/latest_reply.png")


if __name__ == "__main__":
    chat()
