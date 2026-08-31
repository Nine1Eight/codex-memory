def is_glyph_stream(x):
    try:
        return any(ord(c) > 10000 for c in x)
    except:
        return False

def sanitize_input(x):
    if isinstance(x, str) and is_glyph_stream(x):
        return "[GLYPH_BLOCKED]"
    return x
