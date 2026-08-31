from __future__ import annotations
import argparse

def score(progress_probability: float, goal_probability: float, information_gain: float, prediction_confidence: float, failure_probability: float, reset_risk: float, action_cost: float, path_length: int) -> float:
    values = (progress_probability, goal_probability, information_gain, prediction_confidence, failure_probability, reset_risk)
    if any(not 0 <= x <= 1 for x in values): raise ValueError("probabilities must be within [0,1]")
    if action_cost < 0 or path_length < 0: raise ValueError("costs cannot be negative")
    return 3*progress_probability + 2*goal_probability + information_gain + prediction_confidence - 2.5*failure_probability - 1.5*reset_risk - action_cost - 0.01*path_length

def self_test() -> None:
    safe = score(.8,.7,.2,.9,.1,.1,.05,3); risky = score(.8,.7,.2,.9,.8,.8,.05,3)
    assert safe > risky and score(1,1,1,1,0,0,0,0) == 7

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--self-test", action="store_true"); args=parser.parse_args(argv)
    if args.self_test: self_test(); print("RHAE_SELF_TEST_OK")
if __name__ == "__main__": main()
