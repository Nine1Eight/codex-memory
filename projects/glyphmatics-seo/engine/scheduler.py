import time
import subprocess
import sys

CMDS = [
    ["python", "engine/generate.py"],
    ["python", "engine/optimize.py"],
    ["python", "engine/validate.py"],
    ["python", "engine/publish.py"],
    ["python", "engine/build_site.py"],
]

def run_cycle() -> None:
    for cmd in CMDS:
        print("[RUN]", " ".join(cmd))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("[FAIL]", " ".join(cmd), "exit=", result.returncode)
            sys.exit(result.returncode)
    print("[CYCLE COMPLETE]")

if __name__ == "__main__":
    while True:
        run_cycle()
        time.sleep(86400)
