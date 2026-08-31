from PIL import Image

MAX_SIZE = 1333
MIN_SIZE = 800

def normalize_image(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size

    scale = min(MAX_SIZE / max(w, h), 1.0)
    new_w, new_h = int(w * scale), int(h * scale)

    if min(new_w, new_h) < MIN_SIZE:
        scale = MIN_SIZE / min(new_w, new_h)
        new_w, new_h = int(new_w * scale), int(new_h * scale)

    return img.resize((new_w, new_h))
