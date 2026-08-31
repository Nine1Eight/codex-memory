from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "content" / "articles"
DEST = BASE / "site" / "content"

def publish(file_path: Path) -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    out = DEST / file_path.name
    shutil.copy2(file_path, out)

def run() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"Source directory not found: {SRC}")

    for f in sorted(SRC.iterdir()):
        if f.is_file():
            publish(f)
            print("[PUBLISHED]", f.name, "->", DEST / f.name)

if __name__ == "__main__":
    run()
