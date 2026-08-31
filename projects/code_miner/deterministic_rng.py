import random
import hashlib

def set_seed(seed: int):
    random.seed(seed)

def derive_seed(*values):
    h = hashlib.sha256(str(values).encode()).hexdigest()
    return int(h[:8], 16)
