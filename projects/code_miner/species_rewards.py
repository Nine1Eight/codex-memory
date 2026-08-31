def builder_reward(scores, survival, optimizer_retention, novelty):
    return (
        scores["functionality"] * 2 +
        survival * 3 +
        optimizer_retention * 2 +
        novelty
    )

def attacker_reward(unique_failures, reproducibility, market_damage):
    return (
        unique_failures * 5 +
        reproducibility * 3 +
        market_damage * 2
    )

def optimizer_reward(runtime_reduction, ast_reduction, retention):
    return (
        runtime_reduction * 4 +
        ast_reduction * 2 +
        retention * 5
    )
