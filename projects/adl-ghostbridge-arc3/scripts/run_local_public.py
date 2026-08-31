from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from adapters.arc_runtime import BoundRuntimeAdapter
from agent.controller import ARCController
from world.state import Action

def main(argv=None):
    parser=argparse.ArgumentParser(description="Run the production loop against real local public ARC games")
    parser.add_argument("--harness",type=Path,required=True); parser.add_argument("--game",default=""); parser.add_argument("--steps",type=int,default=20); args=parser.parse_args(argv)
    harness=args.harness.resolve()
    if not (harness/"arc3_harness/env_loader.py").is_file(): raise SystemExit(f"invalid harness: {harness}")
    sys.path.insert(0,str(harness))
    from arc3_harness.env_loader import action_input, make_game, select_games
    specs=select_games([args.game] if args.game else None)
    if not specs: raise SystemExit(f"no public game matches {args.game!r}")
    spec=specs[0]
    adapter=BoundRuntimeAdapter({spec.game_id:lambda:make_game(spec)},lambda action,gid:action_input(action.action_id,gid,dict(action.data),{"source":"adl_ghostbridge","prediction_required":action.action_id!=0}))
    controller=ARCController(adapter,ROOT/"checkpoints/public_memory.json",ROOT/"logs/public_run.jsonl")
    result=controller.run_game(spec.game_id,args.steps)
    payload={"validation":"REAL_PUBLIC_ENVIRONMENT","game_id":result.game_id,"steps":result.steps,"level":result.level,"progress":result.progress,"completed":result.completed,"failed":result.failed}
    output=ROOT/"artifacts/public_validation.json"; output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(payload,sort_keys=True))

if __name__=="__main__": main()
