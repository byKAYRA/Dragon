"""Dragon için basit bir uygulama ikonu (icon.ico) üretir.

Gereksinim: Pillow ve Windows fontu. İsteğe bağlıdır; silmek zarar vermez.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def _font(size: int):
    candidates = [
        r"C:\Windows\Fonts\ariblk.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_icon(size: int = 256) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Kenarlıklı yuvarlak zemin (koyu)
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=int(56 * scale),
        fill=(17, 24, 39, 255),
        outline=(59, 130, 246, 255),
        width=max(1, int(10 * scale)),
    )
    # Mavi daire
    draw.ellipse(
        [
            int(48 * scale),
            int(48 * scale),
            int(208 * scale),
            int(208 * scale),
        ],
        fill=(59, 130, 246, 255),
    )

    # Beyaz 'D' harfi
    font = _font(int(120 * scale))
    text = "D"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )
    return image


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    image = make_icon()
    out = ASSETS_DIR / "icon.ico"
    image.save(out, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
    print(f"İkon oluşturuldu: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())