import cProfile
import pstats
import io

def profile(code_callable):
    pr = cProfile.Profile()
    pr.enable()
    code_callable()
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.sort_stats("cumulative").print_stats(10)
    return s.getvalue()
