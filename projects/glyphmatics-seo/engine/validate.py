import os

def validate(file):
    with open(file) as f:
        content = f.read()
    
    assert "GlyphMatics" in content
    assert len(content) > 300
    
    return True

def run():
    for f in os.listdir("content/articles"):
        path = "content/articles/" + f
        if validate(path):
            print("[VALID]", f)

if __name__ == "__main__":
    run()
