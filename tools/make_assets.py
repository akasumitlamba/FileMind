"""Original, deterministic vector-like resource mark; no third-party icon artwork."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
assets = root / "assets"
assets.mkdir(exist_ok=True)
img = Image.new("RGBA", (512, 512), "#0b0b0b")
d = ImageDraw.Draw(img)
d.rounded_rectangle((48, 48, 464, 464), radius=96, fill="#242424")
d.polygon([(116, 158), (235, 158), (272, 196), (396, 196), (396, 355), (116, 355)], fill="#e0e0e0")
d.rounded_rectangle((148, 228, 364, 326), radius=14, fill="#0b0b0b")
d.rounded_rectangle((318, 244, 344, 310), radius=7, fill="#fafafa")
img.save(assets / "grok.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
for size in (16, 24, 32, 44, 48, 50, 64, 128, 150, 256, 310):
    img.resize((size, size), Image.Resampling.LANCZOS).save(assets / f"grok-{size}.png")
img.save(assets / "grok.png")
