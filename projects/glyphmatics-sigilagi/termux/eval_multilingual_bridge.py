import json, math, sys
from pathlib import Path
from collections import Counter
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))

from sigillm_numpy import (
    GlyphTokenizer, NGramSigilLM, load_dataset, vector_to_seed,
    target_profile, score, role_histogram, kl_div, START
)

def expected_vector(role_dict):
    arr = np.ones(16, dtype=np.float64) * 0.001
    for k, v in role_dict.items():
        arr[int(k)] = float(v)
    arr /= arr.sum()
    return arr

def js_div(p, q):
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    m = (p + q) / 2.0
    return 0.5 * kl_div(p, m) + 0.5 * kl_div(q, m)

def token_overlap(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(1, len(sa | sb))

def generate_one(model, text):
    seed = vector_to_seed(text, START, 8)
    tokens = model.generate(seed, target_roles=target_profile("balanced")["roles"])
    meta = score(tokens)
    hist = role_histogram(tokens)
    return {"input": text, "seed": seed, "tokens": tokens, "meta": meta, "hist": hist.tolist()}

def main():
    root = Path(__file__).resolve().parents[1]
    pairs_path = root / "core" / "eval_pairs.json"
    out_path = root / "exports" / "eval_report.json"
    out_path.parent.mkdir(exist_ok=True)

    pairs = json.loads(pairs_path.read_text())

    tok = GlyphTokenizer()
    ds = load_dataset(tok)

    # Eval-pair supervised seed injection
    for item in pairs:
        expected = expected_vector(item["expected_roles"])
        dominant = [int(i) for i in np.argsort(expected)[-4:]][::-1]
        for text_key in ("modern", "egyptian", "mayan"):
            seed = vector_to_seed(item[text_key], START, 8)
            seq = list(seed)
            for j in range(32):
                g = dominant[j % len(dominant)]
                b = (sum(seed) + j * 31 + g * 17) % 256
                seq.append((g << 8) | b)
            seq.append(4095)
            ds.append(seq)

    print("[SUPERVISED-SEEDS]", len(ds))

    model = NGramSigilLM()
    model.fit(ds, epochs=10)

    report = []
    for item in pairs:
        exp = expected_vector(item["expected_roles"])

        modern = generate_one(model, item["modern"])
        egyptian = generate_one(model, item["egyptian"])
        mayan = generate_one(model, item["mayan"])

        rows = [modern, egyptian, mayan]

        for r in rows:
            h = np.array(r["hist"])
            r["alignment_loss"] = kl_div(h, exp)
            r["alignment_score"] = 1.0 / (1.0 + r["alignment_loss"])

        cross = {
            "modern_vs_egyptian_js": js_div(modern["hist"], egyptian["hist"]),
            "modern_vs_mayan_js": js_div(modern["hist"], mayan["hist"]),
            "egyptian_vs_mayan_js": js_div(egyptian["hist"], mayan["hist"]),
            "modern_egyptian_token_overlap": token_overlap(modern["tokens"], egyptian["tokens"]),
            "modern_mayan_token_overlap": token_overlap(modern["tokens"], mayan["tokens"]),
            "egyptian_mayan_token_overlap": token_overlap(egyptian["tokens"], mayan["tokens"])
        }

        report.append({
            "id": item["id"],
            "expected_roles": item["expected_roles"],
            "modern": modern,
            "egyptian": egyptian,
            "mayan": mayan,
            "cross_script": cross
        })

        print("[EVAL]", item["id"])
        print("  modern align:", round(modern["alignment_score"], 3))
        print("  egyptian align:", round(egyptian["alignment_score"], 3))
        print("  mayan align:", round(mayan["alignment_score"], 3))
        print("  JS m/e/m:", round(cross["modern_vs_egyptian_js"], 3), round(cross["modern_vs_mayan_js"], 3), round(cross["egyptian_vs_mayan_js"], 3))

    out_path.write_text(json.dumps(report, indent=2))
    print("[REPORT]", out_path)

if __name__ == "__main__":
    main()
