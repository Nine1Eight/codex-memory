import psutil

def measure(pid):
    p = psutil.Process(pid)
    mem = p.memory_info().rss
    cpu = p.cpu_percent(interval=0.1)
    return mem, cpu
