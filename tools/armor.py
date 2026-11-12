"""
Kosmetik-Ruestungen passend zu den Fluegeln.

Pro Set entstehen zwei Texturen im Vanilla-Ruestungslayout (64x32):
  textures/entity/equipment/humanoid/<id>.png           Helm, Brustplatte (Rumpf + Arme), Schuhe
  textures/entity/equipment/humanoid_leggings/<id>.png  Hose (Huefte + Beine)
dazu equipment/<id>.json (Zuordnung der Lagen) und ein Menue-Icon.

Getragen wird die Ruestung ueber die `equippable`-Komponente (asset_id = cosmetics:<id>);
das Plugin zeigt sie anderen Spielern nur optisch an (siehe ArmorManager).

Layout (x, y, Breite, Hoehe) wie bei Vanilla-Ruestungen:
  Kopf   : oben (8,0) | rechts (0,8) vorne (8,8) links (16,8) hinten (24,8), je 8x8
  Rumpf  : oben (20,16,8,4) | rechts (16,20,4,12) vorne (20,20,8,12) links (28,20,4,12) hinten (32,20,8,12)
  Arm    : oben (44,16,4,4) | (40,20) (44,20) (48,20) (52,20), je 4x12
  Bein   : oben (4,16,4,4)  | (0,20) (4,20) (8,20) (12,20), je 4x12
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class Canvas:
    def __init__(self):
        self.a = np.zeros((32, 64, 4), np.uint8)

    def px(self, x, y, col, alpha=255):
        if 0 <= x < 64 and 0 <= y < 32:
            self.a[y, x] = (*col, alpha)

    def clear(self, x, y, w, h):
        self.a[y:y + h, x:x + w] = 0

    def plate(self, x, y, w, h, st, light_top=True, rim=True):
        """Platte mit Verlauf hell -> dunkel, Lichtkante oben, dunklem Rand."""
        for j in range(h):
            t = j / max(1, h - 1)
            col = lerp(st["light"], st["mid"], min(1, t * 2)) if t < 0.5 else lerp(st["mid"], st["dark"], (t - 0.5) * 2)
            for i in range(w):
                c = col
                if rim and (i == 0 or i == w - 1):
                    c = lerp(col, st["dark"], 0.55)
                self.px(x + i, y + j, c)
        if light_top:
            for i in range(w):
                self.px(x + i, y, lerp(st["light"], (255, 255, 255), 0.4))
        if rim:
            for i in range(w):
                self.px(x + i, y + h - 1, lerp(st["dark"], st["trim"], 0.35))

    def hline(self, x, y, w, col):
        for i in range(w):
            self.px(x + i, y, col)

    def vline(self, x, y, h, col):
        for j in range(h):
            self.px(x, y + j, col)

    def image(self):
        return Image.fromarray(self.a, "RGBA")


def _cracks(c, x, y, w, h, st, rng, n=2):
    """Gluehende Risse (Lava) - kurze Zufallspfade in der Akzentfarbe."""
    for _ in range(n):
        px, py = x + rng.integers(0, w), y + rng.integers(0, h)
        for _ in range(rng.integers(3, 6)):
            c.px(int(px), int(py), st["accent"])
            px = min(x + w - 1, max(x, px + rng.integers(-1, 2)))
            py = min(y + h - 1, max(y, py + 1))


def _emblem(c, x, y, st):
    """Brust-Emblem in einem 8x12-Feld (x, y = linke obere Ecke der Front)."""
    a, g = st["accent"], st["glow"]
    kind = st["emblem"]
    if kind == "cross":       # Seraph: Kreuz mit hellem Kern
        c.vline(x + 3, y + 2, 6, a); c.vline(x + 4, y + 2, 6, a)
        c.hline(x + 2, y + 4, 4, a)
        c.px(x + 3, y + 4, g); c.px(x + 4, y + 4, g)
    elif kind == "fang":      # Daemon: nach unten spitzes Dreieck
        c.hline(x + 1, y + 2, 6, a); c.hline(x + 2, y + 3, 4, a); c.hline(x + 2, y + 4, 4, a)
        c.hline(x + 3, y + 5, 2, a); c.hline(x + 3, y + 6, 2, g); c.px(x + 3, y + 7, a); c.px(x + 4, y + 7, a)
    elif kind == "core":      # Mecha: Reaktorkern mit Fugen
        c.hline(x + 2, y + 3, 4, st["trim"]); c.hline(x + 2, y + 6, 4, st["trim"])
        c.vline(x + 2, y + 3, 4, st["trim"]); c.vline(x + 5, y + 3, 4, st["trim"])
        c.px(x + 3, y + 4, g); c.px(x + 4, y + 4, a); c.px(x + 3, y + 5, a); c.px(x + 4, y + 5, g)
        c.hline(x + 1, y + 9, 6, st["trim"])
    elif kind == "magma":     # Lava: gluehender Spalt
        for j, i in enumerate((3, 4, 3, 4, 4, 3, 4)):
            c.px(x + i, y + 2 + j, g if j in (2, 3) else a)
        c.px(x + 2, y + 4, a); c.px(x + 5, y + 6, a)


def paint_layer1(st, seed=1):
    """Helm, Brustplatte (Rumpf + Arme), Schuhe."""
    rng = np.random.default_rng(seed)
    c = Canvas()
    # --- Helm ---
    for (x, y) in ((8, 0), (0, 8), (8, 8), (16, 8), (24, 8)):
        c.plate(x, y, 8, 8, st)
    c.clear(9, 11, 6, 5)                         # Gesicht offen (Stirn- und Wangenschutz bleiben)
    c.hline(9, 10, 6, lerp(st["dark"], st["trim"], 0.5))
    for x in (11, 12):                           # Kamm ueber Stirn, Scheitel und Hinterkopf
        c.vline(x, 0, 8, st["trim"]); c.vline(x, 8, 2, st["trim"]); c.vline(x + 16, 8, 6, st["trim"])
    c.px(11, 9, st["accent"]); c.px(12, 9, st["accent"])
    for x in (0, 16):                            # Seitenteile: Akzent an der Schlaefe
        c.px(x + 3, 11, st["accent"]); c.px(x + 4, 11, st["accent"]); c.px(x + 3, 12, st["glow"]); c.px(x + 4, 12, st["glow"])
    # --- Rumpf ---
    c.plate(20, 16, 8, 4, st, rim=False)
    for (x, w) in ((16, 4), (20, 8), (28, 4), (32, 8)):
        c.plate(x, 20, w, 12, st)
    c.hline(20, 20, 8, st["trim"]); c.hline(32, 20, 8, st["trim"])       # Kragen
    c.hline(16, 30, 24, st["trim"])                                     # Saum unten
    _emblem(c, 20, 20, st)
    c.vline(35, 22, 7, lerp(st["mid"], st["dark"], 0.6)); c.vline(36, 22, 7, lerp(st["mid"], st["dark"], 0.6))  # Rueckgrat
    # --- Arme: Schulterplatte + Armschiene ---
    c.plate(44, 16, 4, 4, st, rim=False)
    for x in (40, 44, 48, 52):
        c.plate(x, 20, 4, 5, st)
        c.hline(x, 24, 4, st["trim"])
        c.plate(x, 28, 4, 4, st, light_top=False)
        c.hline(x, 28, 4, st["trim"])
    c.px(41, 22, st["accent"]); c.px(42, 22, st["accent"])               # Akzent aussen an der Schulter
    c.px(41, 30, st["accent"]); c.px(42, 30, st["glow"])
    # --- Schuhe (untere 5 Pixel der Beine) ---
    for x in (0, 4, 8, 12):
        c.plate(x, 27, 4, 5, st)
        c.hline(x, 27, 4, st["trim"])
    c.plate(8, 16, 4, 4, st, rim=False, light_top=False)                 # Sohle
    c.px(5, 29, st["accent"]); c.px(6, 29, st["accent"])
    if st.get("cracks"):
        for (x, y, w, h) in ((20, 20, 8, 12), (32, 20, 8, 12), (0, 8, 8, 8), (16, 8, 8, 8), (24, 8, 8, 8),
                             (40, 20, 4, 5), (48, 20, 4, 5), (0, 27, 4, 5), (12, 27, 4, 5)):
            _cracks(c, x, y + 1, w, h - 2, st, rng, n=2)
    return c.image()


def paint_layer2(st, seed=2):
    """Hose: Guertel am Rumpf, Beinschienen."""
    rng = np.random.default_rng(seed)
    c = Canvas()
    for (x, w) in ((16, 4), (20, 8), (28, 4), (32, 8)):                  # Guertel
        c.plate(x, 27, w, 5, st)
        c.hline(x, 27, w, st["trim"])
    c.px(23, 29, st["accent"]); c.px(24, 29, st["accent"]); c.px(23, 30, st["glow"]); c.px(24, 30, st["glow"])
    c.plate(4, 16, 4, 4, st, rim=False)
    for x in (0, 4, 8, 12):                                              # Beine
        c.plate(x, 20, 4, 9, st)
    c.hline(4, 25, 4, st["trim"]); c.px(5, 24, st["accent"]); c.px(6, 24, st["accent"])   # Knie
    c.vline(1, 21, 6, lerp(st["mid"], st["dark"], 0.6))                  # Seitennaht
    if st.get("cracks"):
        for (x, y, w, h) in ((0, 20, 4, 9), (4, 20, 4, 9), (12, 20, 4, 9), (20, 27, 8, 5)):
            _cracks(c, x, y + 1, w, h - 2, st, rng, n=1)
    return c.image()


def render_icon(l1: Image.Image, l2: Image.Image, size=32) -> Image.Image:
    """Flache Vorderansicht (Helm, Brust mit Armen, Hose, Schuhe) als Menue-Icon."""
    doll = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    def put(src, box, pos, flip=False):
        part = src.crop((box[0], box[1], box[0] + box[2], box[1] + box[3]))
        if flip:
            part = part.transpose(Image.FLIP_LEFT_RIGHT)
        doll.alpha_composite(part, pos)
    put(l2, (4, 20, 4, 12), (4, 20)); put(l2, (4, 20, 4, 12), (8, 20), True)      # Beine
    put(l1, (4, 20, 4, 12), (4, 20)); put(l1, (4, 20, 4, 12), (8, 20), True)      # Schuhe
    put(l2, (20, 20, 8, 12), (4, 8))                                              # Guertel
    put(l1, (20, 20, 8, 12), (4, 8))                                              # Brust
    put(l1, (44, 20, 4, 12), (0, 8)); put(l1, (44, 20, 4, 12), (12, 8), True)     # Arme
    put(l1, (8, 8, 8, 8), (4, 0))                                                 # Helm
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(doll, ((size - 16) // 2, (size - 32) // 2))
    return out


def style(dark, mid, light, trim, accent, glow, emblem, **extra):
    d = {"dark": hexc(dark), "mid": hexc(mid), "light": hexc(light), "trim": hexc(trim),
         "accent": hexc(accent), "glow": hexc(glow), "emblem": emblem}
    d.update(extra)
    return d


# id = Fluegel-ID, zu der das Set passt
ARMOR = {
    "angel": style("#8d9cc4", "#dde5f6", "#ffffff", "#e9c46a", "#f2d58a", "#fff8dc", "cross"),
    "demon": style("#12040a", "#4a0f1c", "#7a1c2c", "#1c141a", "#ff4a1c", "#ffb27a", "fang"),
    "mecha": style("#5a6274", "#b4bcc9", "#eef1f6", "#3a4150", "#21c8ff", "#f2ffff", "core"),
    "lava": style("#0e0b0b", "#2e2724", "#4a403a", "#151110", "#ff5a0a", "#ffd34a", "magma", cracks=True),
}


def build_all(ns_dir: Path):
    """Schreibt Texturen, equipment-Definitionen und Icons fuer alle Sets."""
    eq_tex = ns_dir / "textures" / "entity" / "equipment"
    for sub in ("humanoid", "humanoid_leggings"):
        (eq_tex / sub).mkdir(parents=True, exist_ok=True)
    (ns_dir / "equipment").mkdir(parents=True, exist_ok=True)
    for n, (set_id, st) in enumerate(ARMOR.items()):
        l1, l2 = paint_layer1(st, seed=10 + n), paint_layer2(st, seed=50 + n)
        l1.save(eq_tex / "humanoid" / f"{set_id}.png")
        l2.save(eq_tex / "humanoid_leggings" / f"{set_id}.png")
        (ns_dir / "equipment" / f"{set_id}.json").write_text(json.dumps({"layers": {
            "humanoid": [{"texture": f"cosmetics:{set_id}"}],
            "humanoid_leggings": [{"texture": f"cosmetics:{set_id}"}],
        }}, indent=2) + "\n")
        icon_dir = ns_dir / "textures" / "item" / "armor" / set_id
        icon_dir.mkdir(parents=True, exist_ok=True)
        render_icon(l1, l2).save(icon_dir / "icon.png")
        print(f"  {set_id}: Ruestungs-Set")
    return list(ARMOR)
