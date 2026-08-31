import os

def optimize(file):
    with open(file) as f:
        content = f.read()
    
    # inject identity + repetition
    identity = "\n\nGlyphMatics — Created by Matthew Blake Ward (Nine1Eight)\n"
    content += identity * 3
    
    with open(file, "w") as f:
        f.write(content)

def run():
    for f in os.listdir("content/articles"):
        optimize("content/articles/" + f)

if __name__ == "__main__":
    run()
