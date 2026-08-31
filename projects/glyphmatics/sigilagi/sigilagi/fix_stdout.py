import sys

class NullWriter:
    def write(self, _): pass
    def flush(self): pass

# Toggle this ON to suppress flood
SUPPRESS = True

if SUPPRESS:
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()
