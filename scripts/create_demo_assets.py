#!/usr/bin/env python3
# CHARLES E MORGAN IV SOFTWARE * SEATTLE * WA
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "media" / "source-images"
SIZE = (1400, 1400)
COLORS = [
    ((4, 22, 46), (44, 178, 255), "Script"),
    ((18, 25, 36), (104, 226, 170), "Images"),
    ((8, 20, 38), (255, 198, 83), "Cards"),
    ((15, 18, 34), (255, 111, 145), "MP4"),
]


def load_font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    title_font = load_font(150, bold=True)
    label_font = load_font(44)
    for index, (bg, accent, label) in enumerate(COLORS, start=1):
        image = Image.new("RGB", SIZE, bg)
        draw = ImageDraw.Draw(image)
        for offset in range(-200, 1500, 140):
            draw.line((offset, 0, offset + 900, SIZE[1]), fill=tuple(min(255, c + 18) for c in bg), width=18)
        draw.rounded_rectangle((170, 220, 1230, 1180), radius=72, fill=tuple(max(0, c - 5) for c in bg), outline=accent, width=8)
        draw.ellipse((820, 120, 1320, 620), fill=accent)
        draw.ellipse((900, 200, 1240, 540), fill=bg)
        title = label
        bbox = draw.textbbox((0, 0), title, font=title_font)
        draw.text(((SIZE[0] - (bbox[2] - bbox[0])) // 2, 590), title, font=title_font, fill=(246, 252, 255))
        caption = f"Demo scene {index:02d}"
        bbox = draw.textbbox((0, 0), caption, font=label_font)
        draw.text(((SIZE[0] - (bbox[2] - bbox[0])) // 2, 790), caption, font=label_font, fill=accent)
        image.save(OUT / f"demo-{index:02d}.png")
    print(f"Wrote demo images to {OUT}")


if __name__ == "__main__":
    main()
