#!/usr/bin/env python3
"""
Erzeugt alle Texturen, Modelle und Font-Dateien fuer das Resource Pack.

    python3 tools/generate_assets.py

Benoetigt Pillow und numpy (pip install pillow numpy). Die erzeugten Dateien landen in ./resourcepack
und koennen danach auch von Hand (z.B. in Blockbench / Aseprite) ersetzt werden.
"""
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preview  # noqa: E402
import wings  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "resourcepack"
NS = ROOT / "assets" / "cosmetics"
SS = 4  # Supersampling-Faktor fuer weichere Formen vor dem Runterskalieren


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def downsample(big: Image.Image, size, crisp=True) -> Image.Image:
    small = big.resize(size, Image.LANCZOS)
    if crisp:
        # Alpha hart machen -> sauberer Pixel-Look ohne Halo
        r, g, b, a = small.split()
        a = a.point(lambda v: 255 if v >= 110 else 0)
        small = Image.merge("RGBA", (r, g, b, a))
    return small


def item_definition(model: str) -> dict:
    return {"model": {"type": "minecraft:model", "model": model}}


def generated_item(texture: str) -> dict:
    return {"parent": "minecraft:item/generated", "textures": {"layer0": texture}}


# ---------------------------------------------------------------------------
# GUI-Hintergrund (176x222 = 6-reihige Truhe) als Font-Glyph
# ---------------------------------------------------------------------------

def gui_wardrobe() -> Image.Image:
    w, h = 176, 222
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bg_top, bg_bot = (34, 26, 58), (18, 14, 32)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(bg_top, bg_bot, y / h) + (255,))
    # abgerundete Ecken
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=5, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=5, outline=(150, 120, 230, 255), width=1)
    d.rounded_rectangle([1, 1, w - 2, h - 2], radius=4, outline=(70, 52, 120, 255), width=1)

    # Kopfzeile
    d.rounded_rectangle([4, 3, w - 5, 15], radius=3, fill=(64, 46, 112, 255), outline=(120, 95, 200, 255))
    for (sx, sy) in [(150, 6), (158, 10), (165, 7)]:
        d.point([(sx, sy)], fill=(255, 230, 140, 255))
        d.point([(sx - 1, sy), (sx + 1, sy), (sx, sy - 1), (sx, sy + 1)], fill=(200, 170, 90, 255))

    def slot(x, y, fill=(14, 10, 26, 255), edge_dark=(8, 6, 16, 255), edge_light=(92, 72, 150, 255)):
        # x, y = Item-Position (16x16); Rahmen ist 18x18 bei (x-1, y-1)
        d.rectangle([x - 1, y - 1, x + 16, y + 16], fill=fill)
        d.line([(x - 1, y - 1), (x + 16, y - 1)], fill=edge_dark)
        d.line([(x - 1, y - 1), (x - 1, y + 16)], fill=edge_dark)
        d.line([(x - 1, y + 16), (x + 16, y + 16)], fill=edge_light)
        d.line([(x + 16, y - 1), (x + 16, y + 16)], fill=edge_light)

    # Kosmetik-Raster: Reihen 0..3, Spalten 1..7
    for r in range(4):
        for c in range(1, 8):
            slot(8 + c * 18, 18 + r * 18)
    # Seitenleisten links/rechts dekorativ
    for r in range(4):
        y = 18 + r * 18
        d.rectangle([10, y + 4, 21, y + 11], fill=(54, 40, 92, 255))
        d.rectangle([8 + 8 * 18 + 2, y + 4, 8 + 8 * 18 + 13, y + 11], fill=(54, 40, 92, 255))

    # Trennlinie in Reihe 4
    y4 = 18 + 4 * 18 + 8
    d.line([(10, y4), (w - 11, y4)], fill=(110, 86, 180, 255))
    d.line([(10, y4 + 1), (w - 11, y4 + 1)], fill=(40, 30, 70, 255))

    # Button-Reihe (Reihe 5): 45 zurueck, 48 ablegen, 49 schliessen, 53 weiter
    btn_fill = (58, 30, 64, 255)
    for c in (0, 3, 4, 8):
        slot(8 + c * 18, 18 + 5 * 18, fill=btn_fill, edge_light=(200, 120, 220, 255))

    # Spielerinventar
    d.line([(6, 135), (w - 7, 135)], fill=(70, 52, 120, 255))
    for r in range(3):
        for c in range(9):
            slot(8 + c * 18, 140 + r * 18)
    for c in range(9):
        slot(8 + c * 18, 198)
    return img


def gui_button(kind: str) -> Image.Image:
    s = 16 * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(u, v):
        return (u * SS, v * SS)

    if kind == "close":
        d.line([P(3, 3), P(13, 13)], fill=(240, 80, 90, 255), width=3 * SS)
        d.line([P(13, 3), P(3, 13)], fill=(240, 80, 90, 255), width=3 * SS)
    elif kind == "remove":
        d.ellipse([P(2, 2), P(14, 14)], outline=(250, 190, 80, 255), width=2 * SS)
        d.line([P(4.5, 4.5), P(11.5, 11.5)], fill=(250, 190, 80, 255), width=2 * SS)
    elif kind in ("prev", "next"):
        pts = [P(11, 2), P(4, 8), P(11, 14)] if kind == "prev" else [P(5, 2), P(12, 8), P(5, 14)]
        d.polygon(pts, fill=(170, 140, 255, 255), outline=(90, 70, 160, 255))
    return downsample(img, (16, 16))


def pack_icon() -> Image.Image:
    img = gui_wardrobe().crop((0, 0, 176, 176)).resize((64, 64), Image.LANCZOS)
    wings = render_icon("angel", 56)
    img.paste(wings, (4, 6), wings)
    return img


# ---------------------------------------------------------------------------
# Icons aus den echten 3D-Modellen rendern
# ---------------------------------------------------------------------------

def render_icon(wing_id: str, size: int = 32) -> Image.Image:
    img = preview.render_view(wing_id, 0, 8, size=384, zoom=230, with_player=False, center=(0, 1.15, 0),
                              transparent=True)
    bbox = img.getbbox()
    img = img.crop(bbox)
    w, h = img.size
    scale = (size - 2) / max(w, h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    arr = np.asarray(img).copy()
    arr[..., 3] = np.where(arr[..., 3] > 90, 255, 0)
    img = Image.fromarray(arr, "RGBA")
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return out


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def clean_wings() -> None:
    """Alte Fluegel-Dateien entfernen, damit keine Leichen im Pack landen."""
    for sub in ("models/item/wings", "items/wings", "textures/item/wings"):
        d = NS / sub
        if d.exists():
            shutil.rmtree(d)


def main() -> None:
    write_json(ROOT / "pack.mcmeta", {
        "pack": {
            "description": "§dNetzwerk Cosmetics §7- Fluegel & UI",
            # 1.21.4 (46) bis 1.21.8 ueber pack_format/supported_formats,
            # ab 1.21.9 ueber min_format/max_format. 26.3 = 97.
            "pack_format": 46,
            "supported_formats": {"min_inclusive": 46, "max_inclusive": 999},
            "min_format": 46,
            "max_format": 999,
        }
    })

    models = NS / "models" / "item"
    items = NS / "items"
    textures = NS / "textures" / "item"

    clean_wings()
    print("Fluegel:")
    for wid in wings.build_all(NS):
        save_png(render_icon(wid), textures / "wings" / wid / "icon.png")
        write_json(models / "wings" / f"{wid}_icon.json", generated_item(f"cosmetics:item/wings/{wid}/icon"))
        write_json(items / "wings" / f"{wid}_icon.json", item_definition(f"cosmetics:item/wings/{wid}_icon"))
    save_png(pack_icon(), ROOT / "pack.png")

    for kind in ("close", "remove", "prev", "next"):
        save_png(gui_button(kind), textures / "gui" / f"{kind}.png")
        write_json(models / "gui" / f"{kind}.json", generated_item(f"cosmetics:item/gui/{kind}"))
        write_json(items / "gui" / f"{kind}.json", item_definition(f"cosmetics:item/gui/{kind}"))

    # GUI-Hintergruende als Font-Glyphen
    save_png(gui_wardrobe(), NS / "textures" / "gui" / "wardrobe.png")
    write_json(NS / "font" / "gui.json", {
        "providers": [
            # U+E000 = Garderobe (176x222). ascent 13 => Oberkante = Oberkante des Truhen-GUIs
            {"type": "bitmap", "file": "cosmetics:gui/wardrobe.png", "ascent": 13, "height": 222,
             "chars": [chr(0xE000)]},
        ]
    })

    # Leerzeichen-Font fuer pixelgenaue Verschiebung (negativ und positiv)
    advances = {}
    for i in range(10):  # 1, 2, 4, ... 512
        advances[chr(0xF000 + i)] = -(1 << i)
        advances[chr(0xF100 + i)] = (1 << i)
    write_json(NS / "font" / "space.json", {"providers": [{"type": "space", "advances": advances}]})

    print(f"Assets erzeugt in {ROOT}")


if __name__ == "__main__":
    main()
