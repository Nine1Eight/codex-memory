#!/usr/bin/env python3
from vil_feedback_loop import vil_score

def enhance_with_vil(user, rows):
    enhanced = []

    for r in rows:
        base = r.get("meta", {}).get("score", r.get("score", 0.0))
        vs = vil_score(user, r["tokens"], base)

        r["vil_similarity"] = vs["vil_similarity"]
        r["vil_score"] = vs["vil_score"]
        r["final_score"] = vs["final_score"]

        enhanced.append(r)

    enhanced.sort(key=lambda x: x["final_score"], reverse=True)
    return enhanced
