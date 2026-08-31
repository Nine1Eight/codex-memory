import subprocess

def run_containerized(code_path):
    cmd = f"""
    docker run --rm \
        --memory=256m \
        --cpus=1 \
        --pids-limit=64 \
        --read-only \
        -v {code_path}:/app/code.py \
        python:3.12 \
        python /app/code.py
    """
    return subprocess.run(cmd, shell=True, capture_output=True)
