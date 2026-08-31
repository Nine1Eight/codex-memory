from __future__ import annotations
import argparse
from importlib import import_module

def dry_run() -> None:
    modules = ("adapters.arc_runtime","detectors.engine","adl.difference","world.causal","world.twin","ghostbridge.core","planning.reversepath","planning.planner","agent.controller")
    for name in modules: import_module(name)
    print("TERMUX_VALIDATED: deterministic production modules import")
    print("KAGGLE_VALIDATION_REQUIRED: official gateway, GPU/model, and submission scoring")

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--dry-run",action="store_true"); args=parser.parse_args(argv)
    if not args.dry_run: parser.error("provide --dry-run; real execution requires a bound ARC RuntimeAdapter")
    dry_run()
if __name__ == "__main__": main()
