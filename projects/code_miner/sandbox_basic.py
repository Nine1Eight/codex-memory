import subprocess
import resource
import signal

def limit_resources():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))

def run_isolated(cmd):
    return subprocess.run(
        cmd,
        shell=True,
        preexec_fn=limit_resources,
        capture_output=True,
        timeout=5
    )
