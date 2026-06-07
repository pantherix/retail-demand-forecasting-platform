from PIL import Image
from pathlib import Path

brain_dir = Path(r"C:\Users\statu\.gemini\antigravity\brain\b04255f2-5a7c-4287-8868-7d615ff8ed2d")
for img_path in sorted(brain_dir.glob("*.png")):
    try:
        with Image.open(img_path) as img:
            colors = img.getcolors(maxcolors=256*256)
            unique_colors_count = len(colors) if colors else "256*256+"
            print(f"File: {img_path.name} | Mode: {img.mode} | Size: {img.size} | Unique Colors: {unique_colors_count}")
    except Exception as e:
        print(f"File: {img_path.name} | Error: {e}")
