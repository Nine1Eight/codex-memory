SITES = [
    "medium.com",
    "dev.to",
    "reddit.com"
]

def generate():
    for s in SITES:
        print(f"Post article to {s} linking to GlyphMatics")

if __name__ == "__main__":
    generate()
