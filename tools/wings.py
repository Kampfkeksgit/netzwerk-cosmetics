"""
Erzeugt die Fluegel-Modelle und -Texturen (Anime-Stil, eigene Designs).

Koordinaten: Minecraft-Modell-Einheiten (16 = 1 Block). Die Fluegelwurzel liegt bei
(8, 8, 8) = Drehpunkt fuer die Schlag-Animation. Der linke Fluegel waechst Richtung +X,
der rechte ist gespiegelt. Hoehere Z-Werte liegen beim Spieler AUSSEN (vom Ruecken aus
sichtbar), weil das ItemDisplay das Modell um 180 Grad dreht.

Verfuegbar ab 26.x: freie Euler-Rotation pro Element ("x"/"y"/"z") und "light_emission".
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TEX_NS = "cosmetics:item/wings"


# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def r2(v):
    return round(float(v), 3)


class Atlas:
    """Eine Textur, auf die Sprites gepackt werden. Liefert Modell-UVs (0..16)."""

    def __init__(self, name, w=128, h=128):
        self.name = name
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.x = self.y = self.row_h = 0
        self.uv = {}

    def add(self, key, sprite: Image.Image):
        sw, sh = sprite.size
        if self.x + sw > self.w:
            self.x, self.y, self.row_h = 0, self.y + self.row_h + 1, 0
        if self.y + sh > self.h:
            raise ValueError(f"Atlas {self.name} ist voll ({key})")
        self.img.paste(sprite, (self.x, self.y))
        # halbes Pixel Rand nach innen, gegen Bluten an den Kanten
        u0 = (self.x + 0.02) * 16 / self.w
        v0 = (self.y + 0.02) * 16 / self.h
        u1 = (self.x + sw - 0.02) * 16 / self.w
        v1 = (self.y + sh - 0.02) * 16 / self.h
        self.uv[key] = [r2(u0), r2(v0), r2(u1), r2(v1)]
        self.x += sw + 1
        self.row_h = max(self.row_h, sh)
        return self.uv[key]

    def ref(self, wing_id):
        return f"{TEX_NS}/{wing_id}/{self.name}"


# ---------------------------------------------------------------------------
# Sprites malen
# ---------------------------------------------------------------------------

def paint_feather(w, h, pal, tip="round", asym=True, barbs=True, outline=None):
    """Feder, Kiel oben, Spitze unten. Cel-Shading in 3-4 Toenen (Anime-Look)."""
    a = np.zeros((h, w, 4), dtype=np.float32)
    inside = np.zeros((h, w), dtype=bool)
    tone = {}
    for y in range(h):
        t = (y + 0.5) / h
        hw = 0.55 + (w / 2 - 0.55) * smooth((t - 0.06) / 0.28)
        if t > 0.70:
            k = (t - 0.70) / 0.30
            hw *= math.sqrt(max(0.0, 1 - k ** 2)) if tip == "round" else max(0.0, 1 - k) ** 0.75
        for x in range(w):
            dx = x + 0.5 - w / 2
            lim = hw * (0.72 if (asym and dx < 0) else 1.0)
            if abs(dx) <= lim:
                inside[y, x] = True
                tone[(y, x)] = (t, dx, lim)
    oc = outline or pal["outline"]
    for (y, x), (t, dx, lim) in tone.items():
        edge = any(not (0 <= y + dy < h and 0 <= x + ex < w and inside[y + dy, x + ex])
                   for dy, ex in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        if edge:
            c = oc
        else:
            if dx < -0.5:
                c = pal["shade"]
            elif dx > lim - 1.6:
                c = pal["light"]
            else:
                c = pal["base"]
            if abs(dx) < 0.55 and t < 0.9:
                c = pal["shaft"]
            if barbs and t > 0.2 and abs(dx) > 0.6:
                phase = (y + abs(dx) * 0.9) % 7.0
                if phase < 0.9:
                    c = lerp(c, pal["shade2"], 0.22)
            if t < 0.3:
                c = lerp(c, pal["shade2"], (0.3 - t) / 0.3 * 0.55)
            if "tip" in pal and t > pal.get("tip_start", 0.6):
                c = lerp(c, pal["tip"], ((t - pal.get("tip_start", 0.6)) / (1 - pal.get("tip_start", 0.6))) ** 1.1)
        a[y, x, :3] = c
        a[y, x, 3] = 255
    return Image.fromarray(a.astype(np.uint8), "RGBA"), inside


def paint_glow(mask, color, start=0.55, edge=True, alpha=210):
    """Leucht-Ueberlagerung: Rand + Spitzenbereich einer Feder."""
    h, w = mask.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        t = (y + 0.5) / h
        for x in range(w):
            if not mask[y, x]:
                continue
            is_edge = any(not (0 <= y + dy < h and 0 <= x + ex < w and mask[y + dy, x + ex])
                          for dy, ex in ((0, 1), (0, -1), (1, 0), (-1, 0)))
            k = 0.0
            if t > start:
                k = ((t - start) / (1 - start)) ** 1.3
            if edge and is_edge and t > 0.25:
                k = max(k, 0.85)
            if k > 0.12:
                out[y, x, :3] = color
                out[y, x, 3] = int(alpha * min(1.0, k))
    return Image.fromarray(out, "RGBA")


def paint_scallops(w, h, pal, trim=None):
    """Band aus kleinen Deckfedern (fuer den Fluegelarm)."""
    img = Image.new("RGBA", (w * 4, h * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w * 4, h * 4 * 0.45], fill=pal["base"] + (255,))
    for row, (yy, col) in enumerate(((0.35, pal["light"]), (0.62, pal["base"]))):
        for i in range(-1, w // 3 + 2):
            cx = (i * 3 + (1.5 if row else 0)) * 4
            cy = h * 4 * yy
            d.ellipse([cx - 7, cy - 9, cx + 7, cy + 9], fill=col + (255,), outline=pal["outline"] + (255,), width=3)
            d.line([cx, cy - 6, cx, cy + 5], fill=pal["shade"] + (255,), width=2)
    if trim:
        d.rectangle([0, 0, w * 4, 6], fill=trim + (255,))
    small = img.resize((w, h), Image.LANCZOS)
    arr = np.asarray(small).copy()
    arr[..., 3] = np.where(arr[..., 3] > 100, 255, 0)
    return Image.fromarray(arr, "RGBA")


def paint_flat(w, h, top, bottom, outline=None, stripes=None):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=tuple(int(c) for c in lerp(top, bottom, y / max(1, h - 1))) + (255,))
    if stripes:
        for sx, col in stripes:
            d.line([(sx, 0), (sx, h)], fill=col + (255,))
    if outline:
        d.rectangle([0, 0, w - 1, h - 1], outline=outline + (255,))
    return img


def paint_glow_dot(size, inner, outer):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c = (size - 1) / 2
    px = img.load()
    for y in range(size):
        for x in range(size):
            r = math.hypot(x - c, y - c) / (size / 2)
            if r <= 1:
                col = lerp(inner, outer, r)
                px[x, y] = tuple(int(v) for v in col) + (255,)
    return img


# ---------------------------------------------------------------------------
# Elemente bauen
# ---------------------------------------------------------------------------

class ModelBuilder:
    def __init__(self):
        self.elements = []
        self.textures = {}

    def tex(self, var, ref):
        self.textures[var] = ref
        return "#" + var

    def plane(self, name, x0, y0, x1, y1, z, tex, uv, rot=None, origin=None, emission=0, thick=0.1):
        u0, v0, u1, v1 = uv
        el = {
            "name": name,
            "from": [r2(x0), r2(y0), r2(z)],
            "to": [r2(x1), r2(y1), r2(z + thick)],
            "faces": {
                "south": {"uv": [u0, v0, u1, v1], "texture": tex},
                "north": {"uv": [u1, v0, u0, v1], "texture": tex},
            },
        }
        self._finish(el, rot, origin, emission)
        return el

    def cuboid(self, name, f, t, tex, uv, rot=None, origin=None, emission=0, faces=None):
        el = {"name": name, "from": [r2(v) for v in f], "to": [r2(v) for v in t],
              "faces": {face: {"uv": list(uv), "texture": tex}
                        for face in (faces or ("north", "south", "east", "west", "up", "down"))}}
        self._finish(el, rot, origin, emission)
        return el

    def _finish(self, el, rot, origin, emission):
        for v in el["from"] + el["to"]:
            if not -16 <= v <= 32:
                raise ValueError(f"{el['name']}: Koordinate {v} ausserhalb -16..32")
        if rot and any(abs(rot.get(k, 0)) > 1e-6 for k in ("x", "y", "z")):
            el["rotation"] = {"origin": [r2(v) for v in origin],
                              "x": r2(rot.get("x", 0)), "y": r2(rot.get("y", 0)), "z": r2(rot.get("z", 0))}
        if emission:
            el["light_emission"] = int(emission)
        self.elements.append(el)

    def feather(self, name, root, length, width, angle_z, z, tex, uv, twist=0.0, curl=0.0, emission=0):
        """Feder haengt vom Punkt root nach unten, wird um angle_z gefaechert."""
        rx, ry = root
        return self.plane(name, rx - width / 2, ry - length, rx + width / 2, ry, z, tex, uv,
                          rot={"x": -curl, "y": twist, "z": angle_z}, origin=(rx, ry, z), emission=emission,
                          thick=0.08)

    def segment(self, name, p0, p1, width, z0, z1, tex, uv, emission=0, extend=0.4):
        """Quader entlang der Strecke p0 -> p1 (z.B. Knochen, Arm)."""
        (x0, y0), (x1, y1) = p0, p1
        length = math.hypot(x1 - x0, y1 - y0) + extend
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        # Minecraft prueft from/to VOR der Drehung (-16..32). Lange Quader deshalb am Ende
        # verankern, das den ungedrehten Quader innerhalb der Grenzen haelt.
        if x0 - extend / 2 + length <= 32:
            f, t, origin = (x0 - extend / 2, y0 - width / 2, z0), (x0 - extend / 2 + length, y0 + width / 2, z1), (x0, y0)
        else:
            f, t, origin = (x1 + extend / 2 - length, y1 - width / 2, z0), (x1 + extend / 2, y1 + width / 2, z1), (x1, y1)
        return self.cuboid(name, f, t, tex, uv, rot={"z": ang}, origin=(origin[0], origin[1], (z0 + z1) / 2),
                           emission=emission)

    def model(self):
        return {"textures": dict(self.textures, particle=next(iter(self.textures.values()))),
                "elements": self.elements}


def mirror(model: dict) -> dict:
    """Linken Fluegel an x=8 spiegeln -> rechter Fluegel."""
    out = json.loads(json.dumps(model))
    for el in out["elements"]:
        f, t = el["from"], el["to"]
        f[0], t[0] = r2(16 - t[0]), r2(16 - f[0])
        if "rotation" in el:
            r = el["rotation"]
            r["origin"][0] = r2(16 - r["origin"][0])
            if "axis" in r:
                if r["axis"] in ("y", "z"):
                    r["angle"] = -r["angle"]
            else:
                r["y"], r["z"] = r2(-r["y"]), r2(-r["z"])
        faces = el["faces"]
        for fd in faces.values():
            u0, v0, u1, v1 = fd["uv"]
            fd["uv"] = [u1, v0, u0, v1]
        if "east" in faces or "west" in faces:
            faces["east"], faces["west"] = faces.get("west"), faces.get("east")
            for k in ("east", "west"):
                if faces[k] is None:
                    del faces[k]
    return out


# ---------------------------------------------------------------------------
# Fluegel-Skelett
# ---------------------------------------------------------------------------

ARM = [(8.6, 9.6), (11.8, 17.2), (16.8, 22.0), (23.0, 18.8)]
# Hinterkante als quadratische Bezier-Kurve: Koerper -> Bogen unten -> Fluegelspitze
TRAIL = [(9.2, -3.0), (17.0, -19.0), (30.5, 6.5)]
_TRAIL_PTS = None


def trail_points(n=400):
    global _TRAIL_PTS
    if _TRAIL_PTS is None:
        (ax, ay), (cx, cy), (bx, by) = TRAIL
        t = np.linspace(0, 1, n)
        _TRAIL_PTS = np.stack([(1 - t) ** 2 * ax + 2 * (1 - t) * t * cx + t ** 2 * bx,
                               (1 - t) ** 2 * ay + 2 * (1 - t) * t * cy + t ** 2 * by], axis=1)
    return _TRAIL_PTS


def length_to_trail(root, angle_deg):
    """Federlaenge, damit die Spitze (Feder um angle_deg gefaechert) die Hinterkante trifft."""
    a = math.radians(angle_deg)
    d = np.array([math.sin(a), -math.cos(a)])
    rel = trail_points() - np.array(root)
    along = rel @ d
    perp = np.abs(rel[:, 0] * d[1] - rel[:, 1] * d[0])
    perp[along <= 0] = np.inf
    return float(along[int(np.argmin(perp))])


def arm_at(s):
    s = max(0.0, min(3.0, s))
    i = min(2, int(s))
    k = s - i
    (x0, y0), (x1, y1) = ARM[i], ARM[i + 1]
    return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k


def bottom_at(s):
    """Unterkante des Fluegels (Hinterkante) fuer die Federlaengen."""
    return 0.2 - 3.4 * smooth(s / 2.0)


def curl_at(s):
    """Wie weit der Fluegel an dieser Stelle nach hinten gebogen ist (Modell-Z)."""
    return 2.4 * max(0.0, (s - 1.4) / 1.6) ** 2


def angle_at(s):
    """Faecherwinkel der Federn entlang des Arms (0 = senkrecht nach unten)."""
    if s < 2.0:
        return -8 + 14 * (s / 2.0)
    return 6 + 34 * ((s - 2.0) / 1.0) ** 1.15


# ---------------------------------------------------------------------------
# Feder-Fluegel (Seraph, Gefallener Engel, Phoenix)
# ---------------------------------------------------------------------------

def feathered_wing(wing_id, style, tex_dir: Path):
    atlas = Atlas("feathers", 128, 128)
    pal_main, pal_cov = style["feather"], style.get("covert", style["feather"])
    uv = {}
    masks = {}
    for i in range(3):
        img, m = paint_feather(9, 48, pal_main, tip=style.get("tip", "round"))
        uv[f"p{i}"] = atlas.add(f"p{i}", img)
        masks[f"p{i}"] = m
    for i in range(2):
        img, m = paint_feather(9, 44, pal_main, tip="round", asym=False)
        uv[f"s{i}"] = atlas.add(f"s{i}", img)
        masks[f"s{i}"] = m
    img, m = paint_feather(8, 20, pal_cov, tip="round", asym=False, barbs=style.get("covert_barbs", True),
                           outline=style.get("covert_outline"))
    uv["c"] = atlas.add("c", img)
    masks["c"] = m
    img, m = paint_feather(7, 12, pal_cov, tip="round", asym=False, barbs=False, outline=style.get("covert_outline"))
    uv["m"] = atlas.add("m", img)
    masks["m"] = m
    uv["arm"] = atlas.add("arm", paint_scallops(32, 9, pal_cov, trim=style.get("trim")))
    glow = style.get("glow")
    if glow:
        for key in ("p0", "s0", "c"):
            uv["g" + key] = atlas.add("g" + key, paint_glow(masks[key], glow["color"], start=glow.get("start", 0.55),
                                                              alpha=glow.get("alpha", 210)))
    if style.get("embers"):
        uv["ember"] = atlas.add("ember", paint_glow_dot(6, (255, 255, 220), style["embers"]))
    atlas.img.save(tex_dir / "feathers.png")

    b = ModelBuilder()
    t = b.tex("feathers", atlas.ref(wing_id))
    g = glow and glow.get("emission", 15)

    # Primaerfedern (Hand)
    for i in range(10):
        f = i / 9
        s = 2.0 + f
        rx, ry = arm_at(s)
        length = length_to_trail((rx, ry - 0.4), angle_at(s)) + 0.6
        z = 8.0 + curl_at(s) - 0.03 * i
        args = dict(root=(rx, ry - 0.4), length=length, width=3.7, angle_z=angle_at(s), twist=-12 * f, curl=9 * f)
        b.feather(f"primary_{i}", z=z, tex=t, uv=uv[f"p{i % 3}"], **args)
        if glow and glow.get("primaries", True):
            b.feather(f"primary_{i}_glow", z=z + 0.09, tex=t, uv=uv["gp0"], emission=g, **args)
    # Sekundaerfedern (Unterarm + Oberarm)
    for i in range(12):
        f = i / 11
        s = 0.1 + 1.9 * f
        rx, ry = arm_at(s)
        ang = angle_at(s) - 3
        length = length_to_trail((rx, ry - 0.6), ang)
        z = 7.9 + curl_at(s)
        args = dict(root=(rx, ry - 0.6), length=length, width=3.7, angle_z=ang, twist=-5 * f, curl=4 * f)
        b.feather(f"secondary_{i}", z=z, tex=t, uv=uv[f"s{i % 2}"], **args)
        if glow and glow.get("secondaries", False):
            b.feather(f"secondary_{i}_glow", z=z + 0.09, tex=t, uv=uv["gs0"], emission=g, **args)
    # Grosse Deckfedern
    for i in range(14):
        f = i / 13
        s = 0.25 + 2.65 * f
        rx, ry = arm_at(s)
        length = max(6.5, 0.36 * length_to_trail((rx, ry - 0.8), angle_at(s) * 0.85))
        z = 8.45 + curl_at(s)
        args = dict(root=(rx, ry - 0.8), length=length, width=3.2, angle_z=angle_at(s) * 0.85, twist=-6 * f, curl=5 * f)
        b.feather(f"covert_{i}", z=z, tex=t, uv=uv["c"], **args)
        if glow and glow.get("coverts", False):
            b.feather(f"covert_{i}_glow", z=z + 0.09, tex=t, uv=uv["gc"], emission=g, **args)
    # Mittlere Deckfedern
    for i in range(13):
        f = i / 12
        s = 0.15 + 2.6 * f
        rx, ry = arm_at(s)
        b.feather(f"median_{i}", root=(rx, ry - 0.3),
                  length=max(4.2, 0.2 * length_to_trail((rx, ry - 0.3), angle_at(s) * 0.7)), width=2.8,
                  angle_z=angle_at(s) * 0.7, z=8.9 + curl_at(s), tex=t, uv=uv["m"], twist=-4 * f, curl=3 * f)
    # Arm (kleine Deckfedern als Band)
    for k in range(3):
        s0, s1 = k, k + 1
        (x0, y0), (x1, y1) = arm_at(s0), arm_at(s1)
        zc = 9.25 + (curl_at(s0) + curl_at(s1)) / 2
        b.segment(f"arm_{k}", (x0, y0 + 0.2), (x1, y1 + 0.2), 2.6, zc - 0.45, zc + 0.45, t, uv["arm"],
                  emission=style.get("arm_emission", 0))
    # Glut / Funken
    if style.get("embers"):
        rng = np.random.default_rng(7)
        for i in range(10):
            s = 1.6 + 1.4 * rng.random()
            rx, ry = arm_at(s)
            ex = rx + rng.uniform(-1, 3)
            ey = ry - rng.uniform(8, 17)
            ez = 8.6 + curl_at(s) + rng.uniform(0.2, 1.2)
            sz = rng.uniform(0.35, 0.6)
            if -16 < ey - sz and ex + sz < 32:
                b.cuboid(f"ember_{i}", (ex, ey, ez), (ex + sz, ey + sz, ez + sz), t, uv["ember"], emission=15)
    return b.model()


# ---------------------------------------------------------------------------
# Daemon (Membran)
# ---------------------------------------------------------------------------

DEMON_S, DEMON_E, DEMON_W = (8.4, 10.0), (12.0, 18.2), (16.4, 22.6)
DEMON_TIPS = [(28.8, 21.4), (30.6, 11.0), (26.6, 1.0), (18.8, -4.4)]
DEMON_BODY = (8.6, 0.6)
CANVAS = (8.0, -8.0, 32.0, 24.0)  # x0, y0, x1, y1 der Membran-Ebene
PPU = 4  # Pixel pro Modell-Einheit


def to_px(p):
    x0, y0, x1, y1 = CANVAS
    return ((p[0] - x0) * PPU, (y1 - p[1]) * PPU)


def scallop(a, b, toward, depth=0.28, n=8):
    pts = []
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    cx, cy = mx + (toward[0] - mx) * depth, my + (toward[1] - my) * depth
    for i in range(1, n):
        t = i / n
        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t ** 2 * b[0]
        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t ** 2 * b[1]
        pts.append((x, y))
    return pts


def demon_outline():
    pts = [DEMON_S, DEMON_E, DEMON_W, DEMON_TIPS[0]]
    chain = DEMON_TIPS + [DEMON_BODY]
    for a, b in zip(chain, chain[1:]):
        pts += scallop(a, b, DEMON_W if b != DEMON_BODY else DEMON_E, depth=0.3)
        pts.append(b)
    return pts


def membrane_wing(wing_id, style, tex_dir: Path):
    W = int((CANVAS[2] - CANVAS[0]) * PPU)
    H = int((CANVAS[3] - CANVAS[1]) * PPU)
    outline = [to_px(p) for p in demon_outline()]
    mask_img = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask_img).polygon(outline, fill=255)
    mask = np.asarray(mask_img) > 127

    # Membran: Verlauf vom Handgelenk nach aussen + Falten
    yy, xx = np.mgrid[0:H, 0:W]
    wx, wy = to_px(DEMON_W)
    dist = np.hypot(xx - wx, yy - wy) / (W * 1.05)
    c0, c1 = np.array(style["membrane_inner"], float), np.array(style["membrane_outer"], float)
    col = c0[None, None] * (1 - dist[..., None]) + c1[None, None] * dist[..., None]
    angle = np.arctan2(yy - wy, xx - wx)
    folds = (np.sin(angle * 38) > 0.82) & (dist > 0.12)
    col[folds] = col[folds] * 0.72
    # Cel-Schatten unten
    col[dist > 0.62] *= 0.82
    mem = np.zeros((H, W, 4), np.uint8)
    mem[..., :3] = np.clip(col, 0, 255)
    mem[..., 3] = np.where(mask, 255, 0)
    mem_img = Image.fromarray(mem, "RGBA")
    d = ImageDraw.Draw(mem_img)
    d.line(outline + [outline[0]], fill=style["edge"] + (255,), width=2)

    # Leuchtende Adern
    veins = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veins)
    rng = np.random.default_rng(3)
    chain = DEMON_TIPS + [DEMON_BODY]
    for a, b in zip(chain, chain[1:]):
        mid = scallop(a, b, DEMON_W, depth=0.3)[3]
        p0 = (DEMON_W[0] + (a[0] - DEMON_W[0]) * 0.15, DEMON_W[1] + (a[1] - DEMON_W[1]) * 0.15)
        pts = [p0]
        for k in range(1, 6):
            t = k / 5
            px = p0[0] + (mid[0] - p0[0]) * t * 0.88 + rng.uniform(-0.5, 0.5)
            py = p0[1] + (mid[1] - p0[1]) * t * 0.88 + rng.uniform(-0.5, 0.5)
            pts.append((px, py))
        vd.line([to_px(p) for p in pts], fill=style["vein"] + (255,), width=2)
        bx, by = pts[3]
        vd.line([to_px((bx, by)), to_px((bx + rng.uniform(-2, 2), by - rng.uniform(1, 3)))],
                fill=style["vein"] + (255,), width=1)
    glow = veins.filter(ImageFilter.GaussianBlur(1.6))
    veins = Image.alpha_composite(glow, veins)
    va = np.asarray(veins).copy()
    va[..., 3] = np.where(mask, va[..., 3], 0)
    veins = Image.fromarray(va, "RGBA")

    membrane = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    membrane.paste(mem_img, (0, 0))
    membrane.save(tex_dir / "membrane.png")
    glow_tex = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    glow_tex.paste(veins, (0, 0))
    glow_tex.save(tex_dir / "veins.png")

    parts = Atlas("parts", 32, 32)
    uv_bone = parts.add("bone", paint_flat(16, 4, style["bone_light"], style["bone_dark"], outline=style["edge"]))
    uv_claw = parts.add("claw", paint_flat(8, 4, style["claw_light"], style["claw_dark"]))
    parts.img.save(tex_dir / "parts.png")

    b = ModelBuilder()
    tm = b.tex("membrane", f"{TEX_NS}/{wing_id}/membrane")
    tv = b.tex("veins", f"{TEX_NS}/{wing_id}/veins")
    tp = b.tex("parts", f"{TEX_NS}/{wing_id}/parts")
    u1, v1 = r2(W * 16 / 128), r2(H * 16 / 128)
    x0, y0, x1, y1 = CANVAS
    b.plane("membrane", x0, y0, x1, y1, 7.95, tm, [0, 0, u1, v1])
    b.plane("veins_back", x0, y0, x1, y1, 8.08, tv, [0, 0, u1, v1], emission=style.get("vein_emission", 12), thick=0.01)
    b.plane("veins_front", x0, y0, x1, y1, 7.91, tv, [0, 0, u1, v1], emission=style.get("vein_emission", 12), thick=0.01)
    # Knochen
    b.segment("bone_upper", DEMON_S, DEMON_E, 1.5, 7.3, 8.7, tp, uv_bone)
    b.segment("bone_fore", DEMON_E, DEMON_W, 1.3, 7.4, 8.6, tp, uv_bone)
    for i, tip in enumerate(DEMON_TIPS):
        b.segment(f"finger_{i}", DEMON_W, tip, 0.8 if i else 0.9, 7.6, 8.4, tp, uv_bone)
    # Kralle am Handgelenk + Stacheln
    wx_, wy_ = DEMON_W
    b.segment("claw_base", (wx_, wy_), (wx_ - 0.4, wy_ + 2.4), 1.0, 7.5, 8.5, tp, uv_claw)
    b.segment("claw_tip", (wx_ - 0.4, wy_ + 2.3), (wx_ - 1.3, wy_ + 3.6), 0.5, 7.75, 8.25, tp, uv_claw)
    for i, s in enumerate((0.35, 0.7)):
        px = DEMON_S[0] + (DEMON_E[0] - DEMON_S[0]) * s
        py = DEMON_S[1] + (DEMON_E[1] - DEMON_S[1]) * s
        b.segment(f"spike_{i}", (px, py), (px - 1.6, py + 0.9), 0.6, 7.7, 8.3, tp, uv_claw)
    for i, tip in enumerate(DEMON_TIPS[:3]):
        dx, dy = tip[0] - wx_, tip[1] - wy_
        ln = math.hypot(dx, dy)
        end = (min(31.8, tip[0] + dx / ln * 1.2), tip[1] + dy / ln * 1.2)
        b.segment(f"tipclaw_{i}", tip, end, 0.5, 7.75, 8.25, tp, uv_claw)
    return b.model()


# ---------------------------------------------------------------------------
# Fee (durchscheinende Lappen)
# ---------------------------------------------------------------------------

def paint_lobe(w, h, inner, outer, edge, spots, shape="upper"):
    s = 4
    big = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    mask = Image.new("L", (w * s, h * s), 0)
    md = ImageDraw.Draw(mask)
    if shape == "upper":
        md.ellipse([-w * s * 0.15, h * s * 0.05, w * s * 0.98, h * s * 0.95], fill=255)
        md.rectangle([0, h * s * 0.45, w * s * 0.1, h * s * 0.75], fill=255)
    elif shape == "lower":
        md.ellipse([-w * s * 0.1, h * s * 0.02, w * s * 0.95, h * s * 0.98], fill=255)
    else:  # tail
        md.ellipse([w * s * 0.1, 0, w * s * 0.9, h * s * 0.55], fill=255)
        md.ellipse([w * s * 0.25, h * s * 0.45, w * s * 0.75, h * s * 0.99], fill=255)
    m = np.asarray(mask) > 127
    yy, xx = np.mgrid[0:h * s, 0:w * s]
    r = np.clip(np.hypot(xx / (w * s), (yy - h * s / 2) / (h * s)) * 1.25, 0, 1)
    col = np.array(inner, float)[None, None] * (1 - r[..., None]) + np.array(outer, float)[None, None] * r[..., None]
    arr = np.zeros((h * s, w * s, 4), np.uint8)
    arr[..., :3] = col
    arr[..., 3] = np.where(m, (140 + 70 * r).astype(np.uint8), 0)
    big = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(big)
    for ang in np.linspace(-0.7, 0.7, 6):
        d.line([(0, h * s * 0.6), (w * s * math.cos(ang), h * s * (0.6 + 0.6 * math.sin(ang)))],
               fill=edge + (200,), width=s)
    for (fx, fy, fr) in spots:
        d.ellipse([fx * w * s - fr * s, fy * h * s - fr * s, fx * w * s + fr * s, fy * h * s + fr * s],
                  fill=(255, 255, 255, 230))
    out = np.asarray(big).copy()
    out[..., 3] = np.where(m, out[..., 3], 0)
    small = Image.fromarray(out, "RGBA").resize((w, h), Image.LANCZOS)
    sa = np.asarray(small).copy()
    sa[..., 3] = np.where(sa[..., 3] < 50, 0, sa[..., 3])
    # Rand
    alpha = sa[..., 3] > 0
    edge_mask = alpha & ~(np.roll(alpha, 1, 0) & np.roll(alpha, -1, 0) & np.roll(alpha, 1, 1) & np.roll(alpha, -1, 1))
    rim = np.zeros_like(sa)
    rim[edge_mask, :3] = edge
    rim[edge_mask, 3] = 255
    sa[edge_mask, :3] = edge
    sa[edge_mask, 3] = 255
    return Image.fromarray(sa, "RGBA"), Image.fromarray(rim, "RGBA")


def fairy_wing(wing_id, style, tex_dir: Path):
    atlas = Atlas("lobes", 128, 128)
    up, up_rim = paint_lobe(66, 40, style["inner"], style["outer"], style["edge"],
                            [(0.7, 0.35, 1.2), (0.82, 0.55, 0.9), (0.55, 0.25, 0.7)], "upper")
    lo, lo_rim = paint_lobe(46, 44, style["inner2"], style["outer2"], style["edge"],
                            [(0.6, 0.6, 1.0), (0.45, 0.78, 0.7)], "lower")
    tail, tail_rim = paint_lobe(14, 44, style["inner2"], style["outer"], style["edge"], [(0.5, 0.85, 0.8)], "tail")
    uv = {"up": atlas.add("up", up), "lo": atlas.add("lo", lo), "tail": atlas.add("tail", tail),
          "up_rim": atlas.add("up_rim", up_rim), "lo_rim": atlas.add("lo_rim", lo_rim),
          "tail_rim": atlas.add("tail_rim", tail_rim),
          "spark": atlas.add("spark", paint_glow_dot(6, (255, 255, 255), style["edge"]))}
    atlas.img.save(tex_dir / "lobes.png")

    b = ModelBuilder()
    t = b.tex("lobes", atlas.ref(wing_id))
    root = (8.4, 9.6)
    # Oberer Lappen: 22 x 13.3 Einheiten
    lobes = [
        ("upper", (8.2, 4.4, 30.2, 15.7), 8.0, 30, 4, "up"),
        ("lower", (8.2, -6.4, 23.5, 8.2), 8.2, 38, 6, "lo"),
        ("tail", (10.0, -13.5, 14.6, 1.0), 8.4, 44, 10, "tail"),
    ]
    for name, (x0, y0, x1, y1), z, rz, curl, key in lobes:
        rot = {"z": rz, "x": -curl, "y": -6}
        b.plane(f"lobe_{name}", x0, y0, x1, y1, z, t, uv[key], rot=rot, origin=(root[0], root[1], z))
        b.plane(f"lobe_{name}_rim", x0, y0, x1, y1, z + 0.11, t, uv[key + "_rim"], rot=rot,
                origin=(root[0], root[1], z + 0.11), emission=15, thick=0.01)
    rng = np.random.default_rng(11)
    for i in range(9):
        ex, ey = rng.uniform(12, 26), rng.uniform(0, 24)
        ez = rng.uniform(8.6, 9.8)
        sz = rng.uniform(0.3, 0.55)
        b.cuboid(f"spark_{i}", (ex, ey, ez), (ex + sz, ey + sz, ez + sz), t, uv["spark"], emission=15)
    return b.model()


# ---------------------------------------------------------------------------
# Mecha (Panzerrahmen + Energieklingen)
# ---------------------------------------------------------------------------

def paint_blade(w, h, core, edge):
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        t = (y + 0.5) / h
        hw = (w / 2) * (smooth(t / 0.15) if t < 0.15 else 1.0)
        if t > 0.6:
            hw *= max(0.0, 1 - (t - 0.6) / 0.4) ** 0.9
        for x in range(w):
            dx = abs(x + 0.5 - w / 2)
            if dx <= hw:
                k = dx / max(hw, 0.01)
                c = lerp(core, edge, k ** 1.5)
                a = 255 if k > 0.8 else int(170 + 60 * (1 - k))
                img[y, x, :3] = [int(v) for v in c]
                img[y, x, 3] = a
    return Image.fromarray(img, "RGBA")


def mecha_wing(wing_id, style, tex_dir: Path):
    atlas = Atlas("mecha", 64, 64)
    uv = {
        "armor": atlas.add("armor", paint_flat(16, 6, style["armor_light"], style["armor_dark"], outline=style["panel"],
                                               stripes=[(5, style["accent"]), (11, style["panel"])])),
        "joint": atlas.add("joint", paint_flat(6, 6, style["joint_light"], style["joint_dark"], outline=style["panel"])),
        "blade": atlas.add("blade", paint_blade(7, 48, style["core"], style["energy"])),
        "thrust": atlas.add("thrust", paint_glow_dot(6, (255, 255, 255), style["energy"])),
    }
    atlas.img.save(tex_dir / "mecha.png")

    b = ModelBuilder()
    t = b.tex("mecha", atlas.ref(wing_id))
    S, E, W = (8.6, 9.4), (11.4, 16.6), (16.2, 21.4)
    b.segment("frame_upper", S, E, 1.8, 8.1, 9.7, t, uv["armor"])
    b.segment("frame_fore", E, W, 1.6, 8.2, 9.6, t, uv["armor"])
    b.segment("frame_hand", W, (22.4, 20.6), 1.2, 8.35, 9.45, t, uv["armor"])
    for name, (px, py), sz in (("joint_s", S, 2.4), ("joint_e", E, 2.2), ("joint_w", W, 2.0)):
        b.cuboid(name, (px - sz / 2, py - sz / 2, 8.0), (px + sz / 2, py + sz / 2, 8.0 + sz), t, uv["joint"])
    b.cuboid("thruster", (8.6, 6.2, 8.4), (10.0, 7.6, 9.8), t, uv["joint"])
    b.cuboid("thruster_glow", (8.8, 5.6, 8.6), (9.8, 6.2, 9.6), t, uv["thrust"], emission=15)
    blades = [
        (0.0, (22.2, 20.6), 20.0, 36), (0.12, (20.2, 20.9), 21.0, 26), (0.25, (18.2, 21.2), 21.0, 17),
        (0.4, (15.6, 20.4), 19.5, 9), (0.55, (13.6, 18.6), 17.0, 2), (0.7, (12.0, 15.6), 14.0, -4),
        (0.85, (10.4, 12.6), 10.5, -9),
    ]
    for i, (f, (rx, ry), length, ang) in enumerate(blades):
        z = 8.4 + curl_at(2.0 + (1 - f) * 0.9) * 0.6
        b.feather(f"blade_{i}", root=(rx, ry - 1.2), length=length, width=2.8, angle_z=ang, z=z, tex=t,
                  uv=uv["blade"], twist=-8 * (1 - f), curl=6 * (1 - f), emission=15)
        # Halterung
        b.feather(f"mount_{i}", root=(rx, ry + 0.2), length=2.0, width=1.4, angle_z=ang, z=z - 0.4, tex=t,
                  uv=uv["armor"], twist=0, curl=0)
    return b.model()


# ---------------------------------------------------------------------------
# Stile
# ---------------------------------------------------------------------------

def pal(outline, shade2, shade, base, light, shaft, **extra):
    d = {"outline": hexc(outline), "shade2": hexc(shade2), "shade": hexc(shade), "base": hexc(base),
         "light": hexc(light), "shaft": hexc(shaft)}
    for k, v in extra.items():
        d[k] = hexc(v) if isinstance(v, str) else v
    return d


WINGS = {
    "angel": ("feathered", {
        "feather": pal("#8796c0", "#b3c1e2", "#d8e1f4", "#f6f8ff", "#ffffff", "#fff4d6"),
        "covert": pal("#8d9cc4", "#b7c4e4", "#dde5f6", "#f8faff", "#ffffff", "#fff4d6"),
        "covert_barbs": False,
        "trim": hexc("#e9c46a"),
        "glow": {"color": hexc("#fff3c4"), "emission": 9, "start": 0.72, "alpha": 150},
    }),
    "fallen": ("feathered", {
        "feather": pal("#0b0812", "#1a1426", "#2a2238", "#3b3150", "#56497a", "#7b62b5",
                       tip="#5b2a9c", tip_start=0.7),
        "covert": pal("#0b0812", "#1a1426", "#251e33", "#342b47", "#4c4068", "#7b62b5"),
        "tip": "pointed",
        "trim": hexc("#8f5bff"),
        "glow": {"color": hexc("#b47cff"), "emission": 15, "start": 0.68, "alpha": 230, "coverts": True},
    }),
    "phoenix": ("feathered", {
        "feather": pal("#6b1606", "#a3260b", "#d8461a", "#f27a24", "#ffb347", "#ffe2a0",
                       tip="#ffe066", tip_start=0.55),
        "covert": pal("#b33a12", "#c8461a", "#e8642a", "#f8963a", "#ffc46e", "#ffe2a0"),
        "covert_barbs": False,
        "tip": "pointed",
        "trim": hexc("#ffd166"),
        "glow": {"color": hexc("#fff2a8"), "emission": 15, "start": 0.6, "alpha": 230, "secondaries": True},
        "embers": hexc("#ff7b1c"),
    }),
    "demon": ("membrane", {
        "membrane_inner": hexc("#7a0f1f"), "membrane_outer": hexc("#2a0410"), "edge": hexc("#12040a"),
        "vein": hexc("#ff4a1c"), "vein_emission": 12,
        "bone_light": hexc("#4a3a44"), "bone_dark": hexc("#1c141a"),
        "claw_light": hexc("#e8dccb"), "claw_dark": hexc("#8c7a66"),
    }),
    "fairy": ("fairy", {
        "inner": hexc("#c9fbff"), "outer": hexc("#58c9ff"), "inner2": hexc("#f6d6ff"), "outer2": hexc("#b56cff"),
        "edge": hexc("#e9fdff"),
    }),
    "mecha": ("mecha", {
        "armor_light": hexc("#eef1f6"), "armor_dark": hexc("#9aa3b2"), "panel": hexc("#3a4150"),
        "accent": hexc("#2fd3ff"), "joint_light": hexc("#5a6274"), "joint_dark": hexc("#2a2f3a"),
        "core": hexc("#f2ffff"), "energy": hexc("#21c8ff"),
    }),
}

BUILDERS = {"feathered": feathered_wing, "membrane": membrane_wing, "fairy": fairy_wing, "mecha": mecha_wing}


def build_all(ns_dir: Path):
    """Schreibt Texturen, Modelle und Item-Definitionen fuer alle Fluegel."""
    models_dir = ns_dir / "models" / "item" / "wings"
    items_dir = ns_dir / "items" / "wings"
    for wing_id, (kind, style) in WINGS.items():
        tex_dir = ns_dir / "textures" / "item" / "wings" / wing_id
        tex_dir.mkdir(parents=True, exist_ok=True)
        left = BUILDERS[kind](wing_id, style, tex_dir)
        right = mirror(left)
        for side, model in (("left", left), ("right", right)):
            path = models_dir / f"{wing_id}_{side}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(model, indent=1) + "\n")
            item = items_dir / f"{wing_id}_{side}.json"
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text(json.dumps({"model": {"type": "minecraft:model",
                                                  "model": f"cosmetics:item/wings/{wing_id}_{side}"}}, indent=2) + "\n")
        print(f"  {wing_id}: {len(left['elements'])} Elemente pro Seite")
    return list(WINGS)
