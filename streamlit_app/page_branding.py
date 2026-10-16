"""Render the approved mark with minimal padding and no shape distortion."""
from pathlib import Path

from PIL import Image


def tab_icon() -> Image.Image:
    with Image.open(Path(__file__).with_name("mukut_favicon.png")) as source:
        icon = source.convert("RGBA")
    bounds = icon.getchannel("A").point(lambda alpha: 255 if alpha > 200 else 0).getbbox()
    if bounds is None:
        return icon
    left, top, right, bottom = bounds
    # A square crop changes only the canvas. No pixels are stretched or thickened.
    side = min(max(right - left, bottom - top) + 2, icon.width, icon.height)
    x = max(0, min(round((left + right - side) / 2), icon.width - side))
    y = max(0, min(round((top + bottom - side) / 2), icon.height - side))
    return icon.crop((x, y, x + side, y + side))
