#!/usr/bin/env python3
"""
Erzeugt alle Texturen, Modelle und Font-Dateien fuer das Resource Pack.

    python3 tools/generate_assets.py

Benoetigt Pillow (pip install pillow). Die erzeugten Dateien landen in ./resourcepack
und koennen danach auch von Hand (z.B. in Blockbench / Aseprite) ersetzt werden.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

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


# ---------------------------------------------------------------------------
# Fluegel-Texturen (32x32). Wurzel (Ruecken) liegt bei u=0, v~2..12.
# ---------------------------------------------------------------------------

def feather_wing(base_light, base_dark, outline, size=32) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(u, v):
        return (u * SS, v * SS)

    # Federn: (Startpunkt am "Arm", Laenge, Winkel, Breite, Farbe-t)
    feathers = []
    # Primaerfedern (lang, aussen)
    for i in range(6):
        t = i / 5
        start = (14 + t * 15, 3 + t * 1.5)
        angle = math.radians(100 - t * 45)
        length = 26 - t * 12
        feathers.append((start, length, angle, 4.2, 0.85))
    # Sekundaerfedern (mittel, innen)
    for i in range(6):
        t = i / 5
        start = (1.5 + t * 13, 6 + (1 - t) * 2)
        angle = math.radians(95 - t * 5)
        length = 20 + t * 4
        feathers.append((start, length, angle, 4.4, 0.55))

    for (su, sv), length, ang, width, shade in feathers:
        eu = su + math.cos(ang) * length * 0.35
        ev = sv + math.sin(ang) * length
        nx, ny = math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)
        w = width / 2
        poly = [
            P(su - nx * w, sv - ny * w),
            P(eu - nx * w * 0.6, ev - ny * w * 0.6),
            P(eu + (eu - su) * 0.04, ev + 1.8),
            P(eu + nx * w * 0.6, ev + ny * w * 0.6),
            P(su + nx * w, sv + ny * w),
        ]
        d.polygon(poly, fill=lerp(base_dark, base_light, shade) + (255,), outline=outline + (255,), width=SS)

    # Deckfedern / Arm-Band oben
    arm = [P(0, 2), P(10, 0.5), P(22, 0.2), P(31, 3.5), P(30, 6.5), P(20, 6), P(10, 8), P(0, 12)]
    d.polygon(arm, fill=base_light + (255,), outline=outline + (255,), width=SS)
    # kleine Schuppen-Reihe
    for i in range(9):
        u = 2 + i * 3.2
        v = 4.5 + math.sin(i * 0.9) * 0.6 + (1 if i < 3 else 0)
        d.ellipse([P(u - 1.8, v - 1.6), P(u + 1.8, v + 2.4)], fill=lerp(base_light, base_dark, 0.25) + (255,),
                  outline=outline + (255,), width=SS // 2)

    return downsample(img, (size, size))


def membrane_wing(membrane_a, membrane_b, bone, size=32) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(u, v):
        return (u * SS, v * SS)

    root = (0, 7)
    knuckle = (17, 1)
    tip = (31, 2)
    fingers_end = [(31, 2), (29, 16), (23, 26), (14, 31), (5, 28)]
    # Haut (Membran) mit gezackter Unterkante
    outline = [P(*root), P(*knuckle), P(*tip)]
    for i in range(1, len(fingers_end)):
        a, b = fingers_end[i - 1], fingers_end[i]
        mid = ((a[0] + b[0]) / 2 - 3.0, (a[1] + b[1]) / 2 - 2.0)
        outline += [P(*mid), P(*b)]
    outline += [P(0, 16)]
    d.polygon(outline, fill=membrane_a + (255,))

    # Verlauf: Membran unten dunkler
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    for y in range(s):
        gd.line([(0, y), (s, y)], fill=lerp(membrane_a, membrane_b, y / s) + (255,))
    mask = img.split()[3]
    img = Image.composite(grad, img, mask)
    d = ImageDraw.Draw(img)

    # Knochen
    d.line([P(*root), P(*knuckle), P(*tip)], fill=bone + (255,), width=int(2.2 * SS))
    for end in fingers_end[1:]:
        d.line([P(*knuckle), P(*end)], fill=bone + (255,), width=int(1.3 * SS))
    d.ellipse([P(knuckle[0] - 1.6, knuckle[1] - 1.2), P(knuckle[0] + 1.6, knuckle[1] + 2)], fill=bone + (255,))
    # Kralle
    d.polygon([P(knuckle[0] - 1, knuckle[1]), P(knuckle[0] + 1, knuckle[1] - 3.5 + 3), P(knuckle[0] + 3, knuckle[1] - 1)],
              fill=(230, 220, 210, 255))
    return downsample(img, (size, size))


def fairy_wing(col_a, col_b, edge, size=32) -> Image.Image:
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P(u, v):
        return (u * SS, v * SS)

    # Oberer, grosser Fluegellappen
    d.ellipse([P(-2, -1), P(31, 17)], fill=col_a + (190,), outline=edge + (255,), width=SS)
    # Unterer Lappen
    d.ellipse([P(-2, 12), P(19, 31)], fill=col_b + (190,), outline=edge + (255,), width=SS)
    # Adern
    for ang in (-20, -5, 10, 25):
        a = math.radians(ang)
        d.line([P(0, 10), P(0 + math.cos(a) * 30, 10 + math.sin(a) * 14)], fill=edge + (200,), width=SS // 2 + 1)
    for ang in (50, 70, 88):
        a = math.radians(ang)
        d.line([P(0, 13), P(0 + math.cos(a) * 18, 13 + math.sin(a) * 18)], fill=edge + (200,), width=SS // 2 + 1)
    # Glitzerpunkte
    for (u, v) in [(22, 6), (26, 10), (16, 4), (9, 22), (12, 26), (19, 12)]:
        d.ellipse([P(u - 0.9, v - 0.9), P(u + 0.9, v + 0.9)], fill=(255, 255, 255, 255))
    small = img.resize((size, size), Image.LANCZOS)
    r, g, b, a = small.split()
    # weiche, aber nicht zu duenne Transparenz
    a = a.point(lambda v: 0 if v < 40 else min(255, int(v * 1.1)))
    return Image.merge("RGBA", (r, g, b, a))


def wing_icon(wing: Image.Image) -> Image.Image:
    """16x16 Icon: beide Fluegel nebeneinander (gespiegelt)."""
    big = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    big.paste(wing.transpose(Image.FLIP_LEFT_RIGHT), (0, 0))
    big.paste(wing, (32, 0))
    icon = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    scaled = big.resize((16, 9), Image.LANCZOS)
    r, g, b, a = scaled.split()
    a = a.point(lambda v: 255 if v >= 90 else 0)
    scaled = Image.merge("RGBA", (r, g, b, a))
    icon.paste(scaled, (0, 3), scaled)
    return icon


# ---------------------------------------------------------------------------
# Fluegel-Modelle
# ---------------------------------------------------------------------------
# Drehpunkt eines Display-Items ist die Modellmitte (8, 8, 8). Die Fluegelwurzel
# liegt genau dort, damit die Schlag-Animation um die Wurzel rotiert.

def wing_model(side: str) -> dict:
    if side == "left":
        frm, to = [8, -6, 7.9], [28, -6 + 20, 8.1]
        south_uv, north_uv = [0, 0, 16, 16], [16, 0, 0, 16]
    else:
        frm, to = [-12, -6, 7.9], [8, -6 + 20, 8.1]
        south_uv, north_uv = [16, 0, 0, 16], [0, 0, 16, 16]
    return {
        "textures": {"particle": "#wing"},
        "elements": [
            {
                "name": f"wing_{side}",
                "from": frm,
                "to": to,
                "shade": False,
                "faces": {
                    "north": {"uv": north_uv, "texture": "#wing"},
                    "south": {"uv": south_uv, "texture": "#wing"},
                },
            }
        ],
    }


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
    wing = feather_wing((250, 250, 255), (170, 190, 230), (90, 100, 140))
    ic = wing_icon(wing).resize((48, 48), Image.NEAREST)
    img.paste(ic, (8, 8), ic)
    return img


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

WINGS = {
    "angel": lambda: feather_wing((250, 250, 255), (170, 190, 230), (90, 100, 140)),
    "demon": lambda: membrane_wing((140, 20, 30), (40, 5, 15), (25, 18, 22)),
    "fairy": lambda: fairy_wing((120, 230, 255), (220, 140, 255), (70, 60, 160)),
}


def main() -> None:
    write_json(ROOT / "pack.mcmeta", {
        "pack": {
            "description": "§dNetzwerk Cosmetics §7- Fluegel & UI",
            # 1.21.4 (46) bis 1.21.8 ueber pack_format/supported_formats,
            # ab 1.21.9 ueber min_format/max_format.
            "pack_format": 46,
            "supported_formats": {"min_inclusive": 46, "max_inclusive": 999},
            "min_format": 46,
            "max_format": 999,
        }
    })
    save_png(pack_icon(), ROOT / "pack.png")

    models = NS / "models" / "item"
    items = NS / "items"
    textures = NS / "textures" / "item"

    write_json(models / "wings" / "base_left.json", wing_model("left"))
    write_json(models / "wings" / "base_right.json", wing_model("right"))

    for wid, make in WINGS.items():
        tex = make()
        save_png(tex, textures / "wings" / f"{wid}.png")
        save_png(wing_icon(tex), textures / "wings" / f"{wid}_icon.png")
        for side in ("left", "right"):
            write_json(models / "wings" / f"{wid}_{side}.json", {
                "parent": f"cosmetics:item/wings/base_{side}",
                "textures": {"wing": f"cosmetics:item/wings/{wid}"},
            })
            write_json(items / "wings" / f"{wid}_{side}.json", item_definition(f"cosmetics:item/wings/{wid}_{side}"))
        write_json(models / "wings" / f"{wid}_icon.json", generated_item(f"cosmetics:item/wings/{wid}_icon"))
        write_json(items / "wings" / f"{wid}_icon.json", item_definition(f"cosmetics:item/wings/{wid}_icon"))

    for kind in ("close", "remove", "prev", "next"):
        save_png(gui_button(kind), textures / "gui" / f"{kind}.png")
        write_json(models / "gui" / f"{kind}.json", generated_item(f"cosmetics:item/gui/{kind}"))
        write_json(items / "gui" / f"{kind}.json", item_definition(f"cosmetics:item/gui/{kind}"))

    # GUI-Hintergruende als Font-Glyphen
    save_png(gui_wardrobe(), NS / "textures" / "gui" / "wardrobe.png")
    write_json(NS / "font" / "gui.json", {
        "providers": [
            #  = Garderobe (176x222). ascent 13 => Oberkante = Oberkante des Truhen-GUIs
            {"type": "bitmap", "file": "cosmetics:gui/wardrobe.png", "ascent": 13, "height": 222,
             "chars": [""]},
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
