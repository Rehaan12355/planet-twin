"""Globe textures: 4096 x 2048 JPEGs, longitude -180 at the left edge. Display only."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .sources import RAW, TILE_ZOOM

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "textures"
SIZE = (4096, 2048)
Image.MAX_IMAGE_PIXELS = None


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    Image.open(RAW / "textures/earth_blue_marble_4096.jpg").convert("RGB").resize(SIZE).save(OUT / "earth.jpg", quality=85)
    Image.open(RAW / "textures/lroc_color_poles_4k.tif").convert("RGB").resize(SIZE).save(OUT / "moon.jpg", quality=85)
    mars = Image.new("RGB", (256 * 2 ** (TILE_ZOOM + 1), 256 * 2**TILE_ZOOM))
    for row in range(2**TILE_ZOOM):
        for col in range(2 ** (TILE_ZOOM + 1)):
            tile = Image.open(RAW / f"textures/mars_tiles/{TILE_ZOOM}_{row}_{col}.jpg")
            mars.paste(tile, (col * 256, row * 256))
    mars.resize(SIZE).save(OUT / "mars.jpg", quality=85)
    for name in ("earth", "mars", "moon"):
        print(f"texture {name}.jpg {(OUT / (name + '.jpg')).stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
