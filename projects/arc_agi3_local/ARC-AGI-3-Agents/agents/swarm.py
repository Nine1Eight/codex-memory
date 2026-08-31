class Swarm:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def main(self):
        raise RuntimeError("Swarm shim is not used by the direct Termux runner.")
