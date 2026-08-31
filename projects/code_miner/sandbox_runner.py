import subprocess
import tempfile
import os
import resource
import signal
import time
import hashlib
import sys

PYTHON_BIN = "miner_env/bin/python"

TIME_LIMIT = 3              # wall time
CPU_LIMIT_SEC = 2           # CPU time
MEM_LIMIT_MB = 128          # virtual memory cap
MAX_FSIZE = 1_000_000       # file write cap
MAX_PROCESSES = 16          # fork limit
MAX_OPEN_FILES = 32         # fd cap


# -------------------------------
# Resource Limiter
# -------------------------------

def _limit_resources():
    # New process group
    os.setsid()

    # CPU time
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SEC, CPU_LIMIT_SEC))

    # Memory cap
    mem_bytes = MEM_LIMIT_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

    # File size cap
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FSIZE, MAX_FSIZE))

    # Fork bomb protection
    resource.setrlimit(resource.RLIMIT_NPROC, (MAX_PROCESSES, MAX_PROCESSES))

    # File descriptor cap
    resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, MAX_OPEN_FILES))


# -------------------------------
# Hard Kill Utility
# -------------------------------

def _kill_process_tree(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# -------------------------------
# Execution Engine
# -------------------------------

def execute_source(source: str):
    fingerprint = hashlib.sha256(source.encode()).hexdigest()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(source)
        path = f.name

    start = time.time()

    try:
        proc = subprocess.Popen(
            [PYTHON_BIN, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=_limit_resources,
            env={"PYTHONHASHSEED": "0"}  # deterministic hashing
        )

        try:
            stdout, stderr = proc.communicate(timeout=TIME_LIMIT)
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc)
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "timeout",
                "duration": TIME_LIMIT,
                "fingerprint": fingerprint
            }

        duration = time.time() - start

        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "duration": duration,
            "fingerprint": fingerprint
        }

    finally:
        try:
            os.remove(path)
        except Exception:
            pass
