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

def quant(v, steps):
    """Auf `steps` Stufen runden -> Anime-Cel-Look, aber weicher als 3 harte Toene."""
    return round(v * (steps - 1)) / (steps - 1)


def edge_of(mask):
    """Randpixel einer Maske (4er-Nachbarschaft)."""
    m = mask
    inner = (np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    inner[0, :] = inner[-1, :] = False
    inner[:, 0] = inner[:, -1] = False
    return m & ~inner


def paint_feather(w, h, pal, tip="round", asym=True, barbs=True, root_shadow=0.35, steps=6):
    """Feder, Kiel oben, Spitze unten. Weicher Verlauf auf `steps` Stufen: Innenfahne dunkler,
    Aussenfahne heller mit Randlicht, Wurzel im Schatten der Deckfedern, Outline aus der
    abgedunkelten Eigenfarbe statt einheitlich dunkel."""
    out = np.zeros((h, w, 4), dtype=np.float32)
    inside = np.zeros((h, w), dtype=bool)
    info = {}
    for y in range(h):
        t = (y + 0.5) / h
        hw = 0.6 + (w / 2 - 0.6) * smooth((t - 0.03) / 0.22)
        if t > 0.66:
            k = (t - 0.66) / 0.34
            hw *= math.sqrt(max(0.0, 1 - k ** 2.2)) if tip == "round" else max(0.0, 1 - k) ** 0.62
        for x in range(w):
            dx = x + 0.5 - w / 2
            lim = hw * (0.7 if (asym and dx < 0) else 1.0)
            if abs(dx) <= lim:
                inside[y, x] = True
                info[(y, x)] = (t, dx, lim)
    ramp = [pal["shade2"], pal["shade"], pal["base"], pal["light"]]

    def ramp_at(v):
        v = max(0.0, min(1.0, v)) * (len(ramp) - 1)
        i = min(len(ramp) - 2, int(v))
        return lerp(ramp[i], ramp[i + 1], v - i)

    for (y, x), (t, dx, lim) in info.items():
        edge = any(not (0 <= y + dy < h and 0 <= x + ex < w and inside[y + dy, x + ex])
                   for dy, ex in ((0, 1), (0, -1), (1, 0), (-1, 0)))
        across = (dx / lim + 1) / 2 if lim > 0 else 0.5
        v = 0.30 + 0.62 * smooth(across)
        v -= root_shadow * (1 - smooth(t / 0.38))
        v += 0.08 * smooth((t - 0.45) / 0.3)
        if barbs and t > 0.18 and abs(dx) > 0.7:
            if (y * 1.0 + abs(dx) * 1.1) % 6.0 < 0.9:
                v -= 0.09
        c = ramp_at(quant(max(0.0, min(1.0, v)), steps))
        if abs(dx) < 0.5 and t < 0.88:
            c = lerp(c, pal["shaft"], 0.85 * (1 - smooth((t - 0.55) / 0.33)))
        if "tip" in pal and t > pal.get("tip_start", 0.6):
            ts = pal.get("tip_start", 0.6)
            c = lerp(c, pal["tip"], quant(smooth((t - ts) / (1 - ts)), 4))
        if edge:
            c = lerp(c, pal["outline"], 0.72)
            if dx > 0 and 0.2 < t < 0.85:
                c = lerp(pal["light"], pal["outline"], 0.35)
        out[y, x, :3] = c
        out[y, x, 3] = 255
    return Image.fromarray(out.astype(np.uint8), "RGBA"), inside


def paint_glow(mask, color, start=0.55, alpha=210):
    """Leucht-Overlay einer Feder: weicher Anstieg zur Spitze + Saum, halbtransparent."""
    h, w = mask.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        t = (y + 0.5) / h
        for x in range(w):
            if not mask[y, x]:
                continue
            is_edge = any(not (0 <= y + dy < h and 0 <= x + ex < w and mask[y + dy, x + ex])
                          for dy, ex in ((0, 1), (0, -1), (1, 0), (-1, 0)))
            k = quant(smooth((t - start) / (1 - start)), 5) if t > start else 0.0
            if is_edge and t > 0.3:
                k = max(k, 0.55 + 0.4 * smooth((t - 0.3) / 0.5))
            if k > 0.1:
                out[y, x, :3] = color
                out[y, x, 3] = int(alpha * min(1.0, k))
    return Image.fromarray(out, "RGBA")


def paint_arm_band(w, h, pal, trim=None):
    """Bugfedern als Band: drei Reihen kleiner Schuppen, Kante oben im Trim-Ton."""
    S = 4
    img = np.zeros((h * S, w * S, 4), dtype=np.float32)
    yy, xx = np.mgrid[0:h * S, 0:w * S]
    img[..., :3] = pal["base"]
    img[..., 3] = 255
    rows = [(0.30, pal["light"], 0.0), (0.55, pal["base"], 1.5), (0.80, pal["shade"], 0.75)]
    for cy_f, col, off in rows:
        for i in range(-1, w // 3 + 2):
            cx = (i * 3 + off) * S
            cy = h * S * cy_f
            d = ((xx - cx) / (1.6 * S)) ** 2 + ((yy - cy) / (2.3 * S)) ** 2
            m = d <= 1
            img[m, :3] = col
            ring = (d > 0.62) & m
            img[ring, :3] = lerp(col, pal["outline"], 0.55)
    if trim:
        img[: int(1.2 * S), :, :3] = trim
        img[int(1.2 * S): int(1.6 * S), :, :3] = lerp(trim, pal["outline"], 0.4)
    small = Image.fromarray(img.astype(np.uint8), "RGBA").resize((w, h), Image.BOX)
    arr = np.asarray(small).copy()
    arr[..., 3] = 255
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
# Hinterkante als kubische Bezier-Kurve (S-Form): Koerper -> Bogen unten -> Fluegelspitze
TRAIL = [(9.0, -2.4), (12.5, -15.5), (24.0, -15.0), (31.4, 3.0)]
_TRAIL_PTS = None


def trail_points(n=500):
    global _TRAIL_PTS
    if _TRAIL_PTS is None:
        (ax, ay), (b1x, b1y), (b2x, b2y), (cx, cy) = TRAIL
        t = np.linspace(0, 1, n)
        u = 1 - t
        _TRAIL_PTS = np.stack([u ** 3 * ax + 3 * u * u * t * b1x + 3 * u * t * t * b2x + t ** 3 * cx,
                               u ** 3 * ay + 3 * u * u * t * b1y + 3 * u * t * t * b2y + t ** 3 * cy], axis=1)
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
    """Faecherwinkel (0 = senkrecht nach unten): innen leicht nach innen, zur Spitze weit
    aufgefaechert -> spitz zulaufende Hand."""
    if s < 1.8:
        return -10 + 15 * smooth(s / 1.8)
    return 5 + 44 * ((s - 1.8) / 1.2) ** 1.25


# ---------------------------------------------------------------------------
# Feder-Fluegel (Seraph, Gefallener Engel, Phoenix)
# ---------------------------------------------------------------------------

# Basis-Z der Federlagen (vor curl). Bewusst weit auseinander -> sichtbare Tiefe zwischen den Lagen.
Z_SECONDARY = 7.55
Z_PRIMARY = 7.75
Z_GREATER = 8.55
Z_MEDIAN = 9.25
Z_LESSER = 9.85


def feathered_wing(wing_id, style, tex_dir: Path):
    atlas = Atlas("feathers", 256, 256)
    pal_main, pal_cov = style["feather"], style.get("covert", style["feather"])
    tip = style.get("tip", "round")
    uv, masks = {}, {}

    def add(key, res):
        img, m = res
        uv[key] = atlas.add(key, img)
        masks[key] = m

    for i in range(3):
        add(f"p{i}", paint_feather(12, 64, pal_main, tip=tip, root_shadow=0.42))
    for i in range(2):
        add(f"s{i}", paint_feather(12, 58, pal_main, tip="round", asym=False, root_shadow=0.45))
    add("c", paint_feather(10, 26, pal_cov, tip="round", asym=False,
                           barbs=style.get("covert_barbs", True), root_shadow=0.3))
    add("m", paint_feather(9, 16, pal_cov, tip="round", asym=False, barbs=False, root_shadow=0.25))
    uv["arm"] = atlas.add("arm", paint_arm_band(36, 10, pal_cov, trim=style.get("trim")))
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

    # Primaerfedern (Hand): Schindel-Staffelung, aeussere liegt oben, Spitze verlaengert
    n = 12
    for i in range(n):
        f = i / (n - 1)
        s = 1.95 + 1.05 * f
        rx, ry = arm_at(s)
        root = (rx, ry - 0.5)
        ang = angle_at(s)
        length = length_to_trail(root, ang) + 0.9 + 1.6 * smooth((f - 0.6) / 0.4)
        z = Z_PRIMARY + curl_at(s) + 0.045 * i
        args = dict(root=root, length=length, width=4.1, angle_z=ang, twist=-14 * f, curl=10 * f)
        b.feather(f"primary_{i}", z=z, tex=t, uv=uv[f"p{i % 3}"], **args)
        if glow and glow.get("primaries", True):
            b.feather(f"primary_{i}_glow", z=z + 0.085, tex=t, uv=uv["gp0"], emission=g, **args)
    # Sekundaerfedern (Arm)
    n = 14
    for i in range(n):
        f = i / (n - 1)
        s = 0.05 + 1.95 * f
        rx, ry = arm_at(s)
        root = (rx, ry - 0.7)
        ang = angle_at(s) - 2
        length = length_to_trail(root, ang) + 0.3
        z = Z_SECONDARY + curl_at(s) + 0.04 * (n - 1 - i)
        args = dict(root=root, length=length, width=4.0, angle_z=ang, twist=-5 * f, curl=4 * f)
        b.feather(f"secondary_{i}", z=z, tex=t, uv=uv[f"s{i % 2}"], **args)
        if glow and glow.get("secondaries", False):
            b.feather(f"secondary_{i}_glow", z=z + 0.085, tex=t, uv=uv["gs0"], emission=g, **args)
    # Grosse Deckfedern
    n = 15
    for i in range(n):
        f = i / (n - 1)
        s = 0.2 + 2.7 * f
        rx, ry = arm_at(s)
        root = (rx, ry - 0.8)
        ang = angle_at(s) * 0.85
        length = max(7.0, 0.4 * length_to_trail(root, ang))
        z = Z_GREATER + curl_at(s) + 0.03 * i
        args = dict(root=root, length=length, width=3.5, angle_z=ang, twist=-6 * f, curl=5 * f)
        b.feather(f"covert_{i}", z=z, tex=t, uv=uv["c"], **args)
        if glow and glow.get("coverts", False):
            b.feather(f"covert_{i}_glow", z=z + 0.085, tex=t, uv=uv["gc"], emission=g, **args)
    # Mittlere Deckfedern
    n = 14
    for i in range(n):
        f = i / (n - 1)
        s = 0.12 + 2.65 * f
        rx, ry = arm_at(s)
        root = (rx, ry - 0.35)
        ang = angle_at(s) * 0.7
        b.feather(f"median_{i}", root=root, length=max(4.6, 0.22 * length_to_trail(root, ang)), width=3.0,
                  angle_z=ang, z=Z_MEDIAN + curl_at(s) + 0.025 * i, tex=t, uv=uv["m"],
                  twist=-4 * f, curl=3 * f)
    # Arm (kleine Deckfedern als Band)
    for k in range(3):
        (x0, y0), (x1, y1) = arm_at(k), arm_at(k + 1)
        zc = Z_LESSER + (curl_at(k) + curl_at(k + 1)) / 2
        b.segment(f"arm_{k}", (x0, y0 + 0.25), (x1, y1 + 0.25), 2.8, zc - 0.45, zc + 0.45, t, uv["arm"],
                  emission=style.get("arm_emission", 0))
    # Glut / Funken
    if style.get("embers"):
        rng = np.random.default_rng(7)
        for i in range(12):
            s = 1.5 + 1.5 * rng.random()
            rx, ry = arm_at(s)
            ex = rx + rng.uniform(-1, 3)
            ey = ry - rng.uniform(9, 19)
            ez = Z_MEDIAN + curl_at(s) + rng.uniform(0.0, 1.4)
            sz = rng.uniform(0.3, 0.6)
            if -16 < ey - sz and ex + sz < 32:
                b.cuboid(f"ember_{i}", (ex, ey, ez), (ex + sz, ey + sz, ez + sz), t, uv["ember"], emission=15)
    return b.model()


# ---------------------------------------------------------------------------
# Daemon (Membran: Daemon und alle weiteren Membran-Fluegel)
# ---------------------------------------------------------------------------

DEMON_S, DEMON_E, DEMON_W = (8.4, 10.0), (12.0, 18.2), (16.4, 22.6)
DEMON_TIPS = [(28.8, 21.4), (30.6, 11.0), (26.6, 1.0), (18.8, -4.4)]
DEMON_BODY = (8.6, 0.6)
CANVAS = (8.0, -8.0, 32.0, 24.0)  # x0, y0, x1, y1 der Membran-Ebene
PPU = 4  # Pixel pro Modell-Einheit
MEM_Z = 7.95  # Membran-Ebene (vor der Woelbung)


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


def _toward(b):
    return DEMON_W if b != DEMON_BODY else DEMON_E


def demon_outline():
    pts = [DEMON_S, DEMON_E, DEMON_W, DEMON_TIPS[0]]
    chain = DEMON_TIPS + [DEMON_BODY]
    for a, b in zip(chain, chain[1:]):
        pts += scallop(a, b, _toward(b), depth=0.3, n=12)
        pts.append(b)
    return pts


def membrane_panels():
    """Die vier Membranfelder zwischen den Fingern (vom Handgelenk aus). Zusammen = Umriss."""
    chain = DEMON_TIPS + [DEMON_BODY]
    panels = []
    for a, b in zip(chain, chain[1:]):
        pts = [DEMON_W, a] + scallop(a, b, _toward(b), depth=0.3, n=12) + [b]
        if b == DEMON_BODY:
            pts += [DEMON_S, DEMON_E]
        panels.append(pts)
    return panels


def bone_lines():
    lines = [(DEMON_S, DEMON_E), (DEMON_E, DEMON_W)]
    lines += [(DEMON_W, tip) for tip in DEMON_TIPS]
    return lines


def _seg_dist(px, py, a, b):
    """Abstand jedes Pixels zur Strecke a-b (in Pixeln)."""
    ax, ay = to_px(a)
    bx, by = to_px(b)
    vx, vy = bx - ax, by - ay
    t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(px - (ax + t * vx), py - (ay + t * vy))


def _poly_mask(pts, w, h):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([to_px(p) for p in pts], fill=255)
    return np.asarray(m) > 127


def _glow_layer(layer: Image.Image, radius):
    halo = layer.filter(ImageFilter.GaussianBlur(radius))
    return Image.alpha_composite(halo, layer)


def _jitter_path(p0, p1, n, amp, rng):
    """Zickzack-/Adern-Pfad von p0 nach p1 mit seitlichem Versatz."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = math.hypot(dx, dy) or 1
    nx, ny = -dy / ln, dx / ln
    pts = [p0]
    for k in range(1, n):
        t = k / n
        o = rng.uniform(-amp, amp)
        pts.append((p0[0] + dx * t + nx * o, p0[1] + dy * t + ny * o))
    pts.append(p1)
    return pts


def _panel_mid(k):
    chain = DEMON_TIPS + [DEMON_BODY]
    a, b = chain[k], chain[k + 1]
    return scallop(a, b, _toward(b), depth=0.3, n=8)[3]


def paint_membrane_glow(style, w, h, mask):
    """Leuchtmuster der Membran (eigene Ebene mit light_emission)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(style.get("seed", 3))
    vein = style["vein"] + (255,)
    core = style.get("vein_core", style["vein"]) + (255,)
    pattern = style.get("pattern", "veins")
    W_ = DEMON_W

    def line(pts, col, width):
        d.line([to_px(p) for p in pts], fill=col, width=width, joint="curve")

    if pattern in ("veins", "moon"):
        alpha = 255 if pattern == "veins" else 120
        col = style["vein"] + (alpha,)
        for k in range(4):
            mid = _panel_mid(k)
            p0 = (W_[0] + (mid[0] - W_[0]) * 0.12, W_[1] + (mid[1] - W_[1]) * 0.12)
            end = (W_[0] + (mid[0] - W_[0]) * 0.9, W_[1] + (mid[1] - W_[1]) * 0.9)
            main = _jitter_path(p0, end, 6, 0.45, rng)
            line(main, col, 2)
            for j in (2, 4):
                bx, by = main[j]
                ang = math.atan2(end[1] - p0[1], end[0] - p0[0]) + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9)
                ln = rng.uniform(2.0, 3.6)
                line(_jitter_path((bx, by), (bx + math.cos(ang) * ln, by + math.sin(ang) * ln), 3, 0.25, rng), col, 1)
    if pattern == "cracks":
        # Netz aus Rissen, die von den Knochen ausgehen
        for a, b in bone_lines()[1:]:
            for j in range(3):
                t = rng.uniform(0.2, 0.85)
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                ang = rng.uniform(0, 2 * math.pi)
                pts = [p]
                for _ in range(rng.integers(3, 6)):
                    ang += rng.uniform(-0.9, 0.9)
                    ln = rng.uniform(1.4, 3.0)
                    pts.append((pts[-1][0] + math.cos(ang) * ln, pts[-1][1] + math.sin(ang) * ln))
                line(pts, vein, 3)
                line(pts, core, 1)
    if pattern == "lightning":
        for k in range(4):
            mid = _panel_mid(k)
            p0 = (W_[0] + (mid[0] - W_[0]) * 0.1, W_[1] + (mid[1] - W_[1]) * 0.1)
            bolt = _jitter_path(p0, mid, 7, 1.1, rng)
            line(bolt, vein, 3)
            line(bolt, core, 1)
            bx, by = bolt[3]
            br = _jitter_path((bx, by), (bx + rng.uniform(-3, 3), by - rng.uniform(2, 4)), 3, 0.6, rng)
            line(br, vein, 2)
            line(br, core, 1)
    if pattern == "frost":
        # Kristalline Aeste entlang der Felder, Seitenaeste im 60-Grad-Winkel
        for k in range(4):
            mid = _panel_mid(k)
            p0 = (W_[0] + (mid[0] - W_[0]) * 0.15, W_[1] + (mid[1] - W_[1]) * 0.15)
            line([p0, mid], vein, 1)
            ang = math.atan2(mid[1] - p0[1], mid[0] - p0[0])
            for t in (0.3, 0.5, 0.7, 0.85):
                bx, by = p0[0] + (mid[0] - p0[0]) * t, p0[1] + (mid[1] - p0[1]) * t
                ln = 2.6 * (1 - t) + 0.8
                for s in (-1, 1):
                    a2 = ang + s * math.radians(60)
                    line([(bx, by), (bx + math.cos(a2) * ln, by + math.sin(a2) * ln)], core, 1)
    if pattern == "stars":
        px = rng.integers(0, w, 900)
        py = rng.integers(0, h, 900)
        ok = mask[py, px]
        px, py = px[ok][:85], py[ok][:85]
        for i, (x, y) in enumerate(zip(px, py)):
            c = core if i % 3 else vein
            if i % 9 == 0:
                d.line([(x - 1, y), (x + 1, y)], fill=c)
                d.line([(x, y - 1), (x, y + 1)], fill=c)
            else:
                d.point([(x, y)], fill=c)
    if pattern == "moon":
        cx, cy, r = 23.2, 13.9, 2.1
        disc = Image.new("L", (w, h), 0)
        dd = ImageDraw.Draw(disc)
        (mx, my), rp = to_px((cx, cy)), r * PPU
        dd.ellipse([mx - rp, my - rp, mx + rp, my + rp], fill=255)
        cut = rp * 0.78
        ox, oy = mx + rp * 0.45, my - rp * 0.3
        dd.ellipse([ox - cut, oy - cut, ox + cut, oy + cut], fill=0)
        moon = Image.new("RGBA", (w, h), style["moon"] + (255,))
        moon.putalpha(disc)
        halo = Image.new("RGBA", (w, h), style.get("moon_glow", style["vein"]) + (255,))
        halo.putalpha(disc.filter(ImageFilter.GaussianBlur(3)))
        img = Image.alpha_composite(img, halo)
        img = Image.alpha_composite(img, moon)
        d = ImageDraw.Draw(img)
    img = _glow_layer(img, style.get("glow_radius", 1.6))
    if style.get("rim_glow"):
        edge = edge_of(mask)
        band = edge | edge_of(mask & ~edge)
        rim = np.zeros((h, w, 4), np.uint8)
        rim[band, :3] = style["rim_glow"]
        rim[band, 3] = 150
        rim[edge, 3] = 255
        img = Image.alpha_composite(img, Image.fromarray(rim, "RGBA"))
    return img


def paint_membrane_base(style, w, h, mask):
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    wx, wy = to_px(DEMON_W)
    dist = np.clip(np.hypot(xx - wx, yy - wy) / (w * 1.05), 0, 1)
    q = np.round(dist * 5) / 5
    c0, c1 = np.array(style["membrane_inner"], float), np.array(style["membrane_outer"], float)
    col = c0[None, None] * (1 - q[..., None]) + c1[None, None] * q[..., None]
    # Membran haengt zwischen den Knochen durch: an den Knochen dunkler, Feldmitte heller
    db = np.min([_seg_dist(xx, yy, a, b) for a, b in bone_lines()], axis=0) / PPU
    lift = np.round(np.clip(db / 3.2, 0, 1) * 3) / 3
    col *= (0.74 + 0.30 * lift)[..., None]
    # weiche Falten strahlenfoermig vom Handgelenk
    ang = np.arctan2(yy - wy, xx - wx)
    fold = np.clip((np.sin(ang * 38) - 0.7) / 0.3, 0, 1) * (dist > 0.12)
    col *= (1 - 0.16 * np.round(fold * 2) / 2)[..., None]
    edge = edge_of(mask)
    inner_rim = edge_of(mask & ~edge)
    col[inner_rim] *= 0.8
    col[edge] = style["edge"]
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(col, 0, 255)
    out[..., 3] = np.where(mask, style.get("alpha", 255), 0)
    out[edge, 3] = 255
    return Image.fromarray(out, "RGBA")


def paint_bone(w, h, light, dark, edge):
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        t = y / max(1, h - 1)
        c = lerp(light, dark, quant(t, 4))
        if y == 0:
            c = lerp(light, (255, 255, 255), 0.3)
        if y == h - 1:
            c = lerp(dark, edge, 0.6)
        img[y, :, :3] = [int(v) for v in c]
    img[..., 3] = 255
    img[:, 0, :3] = img[:, -1, :3] = [int(v) for v in lerp(dark, edge, 0.5)]
    return Image.fromarray(img, "RGBA")


def membrane_wing(wing_id, style, tex_dir: Path):
    w = int((CANVAS[2] - CANVAS[0]) * PPU)
    h = int((CANVAS[3] - CANVAS[1]) * PPU)
    full = _poly_mask(demon_outline(), w, h)
    if style.get("holes"):
        # zerfetzte Membran: Loecher nahe der Hinterkante, Raender leuchten
        rng = np.random.default_rng(style.get("seed", 3) + 1)
        holes = Image.new("L", (w, h), 0)
        hd = ImageDraw.Draw(holes)
        for k in range(4):
            mid = _panel_mid(k)
            for _ in range(2):
                t = rng.uniform(0.62, 0.86)
                cx = DEMON_W[0] + (mid[0] - DEMON_W[0]) * t + rng.uniform(-1, 1)
                cy = DEMON_W[1] + (mid[1] - DEMON_W[1]) * t + rng.uniform(-1, 1)
                (px, py), r = to_px((cx, cy)), rng.uniform(1.6, 3.2)
                hd.ellipse([px - r, py - r * 1.3, px + r, py + r * 1.3], fill=255)
        hole = np.asarray(holes) > 127
        full = full & ~hole
        style = dict(style, rim_glow=style["vein"])
    base = paint_membrane_base(style, w, h, full)
    glow = paint_membrane_glow(style, w, h, full)
    ga = np.asarray(glow).copy()
    ga[..., 3] = np.where(full, ga[..., 3], 0)
    glow = Image.fromarray(ga, "RGBA")

    # Je Feld ein Ausschnitt (1 px ueberlappend gegen Naehte) im 2x2-Atlas
    mem_atlas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    glow_atlas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    panels = membrane_panels()
    panel_uv = []
    for k, pts in enumerate(panels):
        pm = _poly_mask(pts, w, h)
        pm = pm | np.roll(pm, 1, 0) | np.roll(pm, -1, 0) | np.roll(pm, 1, 1) | np.roll(pm, -1, 1)
        pm &= full
        ox, oy = (k % 2) * w, (k // 2) * h
        for src, dst in ((base, mem_atlas), (glow, glow_atlas)):
            a = np.asarray(src).copy()
            a[..., 3] = np.where(pm, a[..., 3], 0)
            dst.paste(Image.fromarray(a, "RGBA"), (ox, oy))
        panel_uv.append([r2(ox * 16 / 256), r2(oy * 16 / 256), r2((ox + w) * 16 / 256), r2((oy + h) * 16 / 256)])
    mem_atlas.save(tex_dir / "membrane.png")
    glow_atlas.save(tex_dir / "veins.png")

    parts = Atlas("parts", 64, 64)
    uv_bone = parts.add("bone", paint_bone(16, 5, style["bone_light"], style["bone_dark"], style["edge"]))
    uv_joint = parts.add("joint", paint_glow_dot(6, style["bone_light"], style["bone_dark"]))
    uv_claw = parts.add("claw", paint_flat(8, 4, style["claw_light"], style["claw_dark"]))
    uv_ember = parts.add("ember", paint_glow_dot(6, (255, 255, 220), style.get("embers", style["vein"])))
    parts.img.save(tex_dir / "parts.png")

    b = ModelBuilder()
    tm = b.tex("membrane", f"{TEX_NS}/{wing_id}/membrane")
    tv = b.tex("veins", f"{TEX_NS}/{wing_id}/veins")
    tp = b.tex("parts", f"{TEX_NS}/{wing_id}/parts")
    x0, y0, x1, y1 = CANVAS
    em = style.get("vein_emission", 12)
    billow = style.get("billow", -0.75)  # negativ = Feld woelbt sich zum Koerper, Knochen stehen vor
    for k, pts in enumerate(panels):
        cx = sum(p[0] for p in pts) / len(pts) - DEMON_W[0]
        cy = sum(p[1] for p in pts) / len(pts) - DEMON_W[1]
        ln = math.hypot(cx, cy)
        s = billow / ln
        # z' ~ s * (Abstand vom Handgelenk in Feldrichtung): Rx kippt mit y, Ry mit x
        rot = {"x": math.degrees(math.asin(max(-1, min(1, s * cy / ln)))),
               "y": math.degrees(math.asin(max(-1, min(1, -s * cx / ln))))}
        for name, z, tex, thick, emi in ((f"membrane_{k}", MEM_Z, tm, 0.1, 0),
                                         (f"glow_back_{k}", MEM_Z + 0.13, tv, 0.01, em),
                                         (f"glow_front_{k}", MEM_Z - 0.04, tv, 0.01, em)):
            b.plane(name, x0, y0, x1, y1, z, tex, panel_uv[k], rot=rot, origin=(DEMON_W[0], DEMON_W[1], z),
                    emission=emi, thick=thick)
    # Knochen: Ober- und Unterarm kraeftig, Finger zweigeteilt und zur Spitze duenner
    b.segment("bone_upper", DEMON_S, DEMON_E, 1.7, 7.2, 8.8, tp, uv_bone)
    b.segment("bone_fore", DEMON_E, DEMON_W, 1.5, 7.3, 8.7, tp, uv_bone)
    for i, tip in enumerate(DEMON_TIPS):
        mid = (DEMON_W[0] + (tip[0] - DEMON_W[0]) * 0.55, DEMON_W[1] + (tip[1] - DEMON_W[1]) * 0.55)
        b.segment(f"finger_{i}_a", DEMON_W, mid, 1.0 if i == 0 else 0.9, 7.45, 8.55, tp, uv_bone)
        b.segment(f"finger_{i}_b", mid, tip, 0.75 if i == 0 else 0.65, 7.55, 8.45, tp, uv_bone)
        b.cuboid(f"knuckle_{i}", (mid[0] - 0.5, mid[1] - 0.5, 7.5), (mid[0] + 0.5, mid[1] + 0.5, 8.5), tp, uv_joint)
    for name, (px, py), sz in (("joint_elbow", DEMON_E, 1.9), ("joint_wrist", DEMON_W, 1.7)):
        b.cuboid(name, (px - sz / 2, py - sz / 2, 8.0 - sz / 2), (px + sz / 2, py + sz / 2, 8.0 + sz / 2), tp, uv_joint)
    # Kralle am Handgelenk + Stacheln am Oberarm
    ce = style.get("claw_emission", 0)
    wx_, wy_ = DEMON_W
    b.segment("claw_base", (wx_, wy_), (wx_ - 0.4, wy_ + 2.4), 1.0, 7.5, 8.5, tp, uv_claw, emission=ce)
    b.segment("claw_tip", (wx_ - 0.4, wy_ + 2.3), (wx_ - 1.3, wy_ + 3.6), 0.5, 7.75, 8.25, tp, uv_claw, emission=ce)
    for i, s_ in enumerate((0.35, 0.7)):
        px = DEMON_S[0] + (DEMON_E[0] - DEMON_S[0]) * s_
        py = DEMON_S[1] + (DEMON_E[1] - DEMON_S[1]) * s_
        b.segment(f"spike_{i}", (px, py), (px - 1.6, py + 0.9), 0.6, 7.7, 8.3, tp, uv_claw, emission=ce)
    # Krallen an den Fingerspitzen, leicht nach unten gehakt
    for i, tip in enumerate(DEMON_TIPS[:3]):
        dx, dy = tip[0] - wx_, tip[1] - wy_
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        p1 = (min(31.6, tip[0] + ux * 0.9), tip[1] + uy * 0.9)
        p2 = (min(31.9, p1[0] + ux * 0.4 + uy * 0.5), p1[1] + uy * 0.4 - ux * 0.5)
        b.segment(f"tipclaw_{i}", tip, p1, 0.55, 7.72, 8.28, tp, uv_claw, emission=ce)
        b.segment(f"tipclaw_{i}_hook", p1, p2, 0.35, 7.82, 8.18, tp, uv_claw, emission=ce)
    if style.get("embers"):
        rng = np.random.default_rng(5)
        for i, tip in enumerate(DEMON_TIPS[:3]):
            ex, ey = min(31.2, tip[0] + rng.uniform(-0.4, 0.2)), tip[1] - rng.uniform(1.0, 2.2)
            sz = rng.uniform(0.35, 0.5)
            b.cuboid(f"ember_{i}", (ex, ey, 7.8), (ex + sz, ey + sz, 7.8 + sz), tp, uv_ember, emission=15)
        for i in range(3):
            ex, ey = rng.uniform(16, 27), rng.uniform(-9, -3)
            sz = rng.uniform(0.3, 0.45)
            b.cuboid(f"ember_fall_{i}", (ex, ey, 7.6), (ex + sz, ey + sz, 7.6 + sz), tp, uv_ember, emission=15)
    return b.model()


# ---------------------------------------------------------------------------
# Fee (durchscheinende Lappen)
# ---------------------------------------------------------------------------

def paint_lobe(w, h, inner, outer, edge, spots, shape="upper", mid=None):
    """Fluegellappen mit 3-Stufen-Verlauf (innen -> mitte -> aussen), feinen Adern, weichen
    Glanzpunkten und hellem Innensaum. Liefert (Lappen, Leuchtrand)."""
    s = 4
    W_, H_ = w * s, h * s
    mask = Image.new("L", (W_, H_), 0)
    md = ImageDraw.Draw(mask)
    if shape == "upper":
        md.ellipse([-W_ * 0.12, H_ * 0.08, W_ * 0.96, H_ * 0.97], fill=255)
        md.polygon([(W_ * 0.42, H_ * 0.14), (W_ * 0.99, H_ * 0.02), (W_ * 0.9, H_ * 0.42)], fill=255)
        md.rectangle([0, H_ * 0.45, W_ * 0.1, H_ * 0.75], fill=255)
    elif shape == "lower":
        md.ellipse([-W_ * 0.1, H_ * 0.02, W_ * 0.94, H_ * 0.9], fill=255)
    else:  # tail
        md.ellipse([W_ * 0.12, 0, W_ * 0.88, H_ * 0.55], fill=255)
        md.ellipse([W_ * 0.22, H_ * 0.45, W_ * 0.78, H_ * 0.99], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(s * 0.6))
    m = np.asarray(mask) > 127
    yy, xx = np.mgrid[0:H_, 0:W_]
    r = np.clip(np.hypot(xx / W_, (yy - H_ * 0.6) / H_) * 1.25, 0, 1)
    rq = np.round(r * 5) / 5
    mid = mid or lerp(inner, outer, 0.5)
    c_in, c_mid, c_out = (np.array(c, float)[None, None] for c in (inner, mid, outer))
    k = rq[..., None]
    col = np.where(k < 0.5, c_in * (1 - k * 2) + c_mid * (k * 2), c_mid * (2 - k * 2) + c_out * (k * 2 - 1))
    arr = np.zeros((H_, W_, 4), np.uint8)
    arr[..., :3] = np.clip(col, 0, 255)
    arr[..., 3] = np.where(m, (130 + 80 * rq).astype(np.uint8), 0)
    big = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(big)
    vein = tuple(int(v) for v in lerp(edge, outer, 0.3)) + (170,)
    root = (0, H_ * 0.6)
    for ang in np.linspace(-0.75, 0.75, 7):
        pts = []
        for t in np.linspace(0, 1, 12):
            bend = 0.18 * math.sin(t * math.pi) * (1 if ang >= 0 else -1)
            pts.append((root[0] + W_ * t * math.cos(ang + bend), root[1] + H_ * 0.62 * t * math.sin(ang + bend)))
        d.line(pts, fill=vein, width=s, joint="curve")
    spot = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    sd = ImageDraw.Draw(spot)
    for (fx, fy, fr) in spots:
        for rr, a in ((fr * 1.8, 70), (fr * 1.2, 140), (fr * 0.6, 240)):
            sd.ellipse([fx * W_ - rr * s, fy * H_ - rr * s, fx * W_ + rr * s, fy * H_ + rr * s],
                       fill=(255, 255, 255, a))
    big = Image.alpha_composite(big, spot)
    out = np.asarray(big).copy()
    out[..., 3] = np.where(m, out[..., 3], 0)
    small = Image.fromarray(out, "RGBA").resize((w, h), Image.LANCZOS)
    sa = np.asarray(small).copy()
    sa[..., 3] = np.where(sa[..., 3] < 60, 0, sa[..., 3])
    alpha = sa[..., 3] > 0
    edge_mask = edge_of(alpha)
    band = edge_of(alpha & ~edge_mask)
    sa[band, :3] = [int(v) for v in lerp(edge, outer, 0.25)]
    sa[edge_mask, :3] = edge
    sa[edge_mask, 3] = 255
    rim = np.zeros_like(sa)
    rim[edge_mask, :3] = edge
    rim[edge_mask, 3] = 255
    rim[band, :3] = edge
    rim[band, 3] = 90
    return Image.fromarray(sa, "RGBA"), Image.fromarray(rim, "RGBA")


def fairy_wing(wing_id, style, tex_dir: Path):
    atlas = Atlas("lobes", 256, 256)
    up, up_rim = paint_lobe(132, 80, style["inner"], style["outer"], style["edge"],
                            [(0.7, 0.35, 1.2), (0.82, 0.55, 0.9), (0.55, 0.25, 0.7), (0.9, 0.2, 0.5)], "upper",
                            mid=style.get("mid"))
    lo, lo_rim = paint_lobe(92, 88, style["inner2"], style["outer2"], style["edge"],
                            [(0.6, 0.6, 1.0), (0.45, 0.78, 0.7), (0.75, 0.85, 0.5)], "lower", mid=style.get("mid2"))
    tail, tail_rim = paint_lobe(28, 88, style["inner2"], style["outer"], style["edge"], [(0.5, 0.85, 0.8)], "tail")
    uv = {"up": atlas.add("up", up), "lo": atlas.add("lo", lo), "tail": atlas.add("tail", tail),
          "up_rim": atlas.add("up_rim", up_rim), "lo_rim": atlas.add("lo_rim", lo_rim),
          "tail_rim": atlas.add("tail_rim", tail_rim),
          "spark": atlas.add("spark", paint_glow_dot(6, (255, 255, 255), style["edge"]))}
    atlas.img.save(tex_dir / "lobes.png")

    b = ModelBuilder()
    t = b.tex("lobes", atlas.ref(wing_id))
    root = (8.4, 9.6)
    # Lappen deutlich gestaffelt (Z) und unterschiedlich stark nach hinten gebogen -> Tiefe
    lobes = [
        ("upper", (8.2, 4.4, 30.2, 15.7), 7.8, 30, 4, "up"),
        ("lower", (8.2, -6.4, 23.5, 8.2), 8.35, 38, 8, "lo"),
        ("tail", (10.0, -13.5, 14.6, 1.0), 8.9, 44, 12, "tail"),
    ]
    for name, (x0, y0, x1, y1), z, rz, curl, key in lobes:
        rot = {"z": rz, "x": -curl, "y": -6}
        b.plane(f"lobe_{name}", x0, y0, x1, y1, z, t, uv[key], rot=rot, origin=(root[0], root[1], z))
        b.plane(f"lobe_{name}_rim", x0, y0, x1, y1, z + 0.11, t, uv[key + "_rim"], rot=rot,
                origin=(root[0], root[1], z + 0.11), emission=15, thick=0.01)
    rng = np.random.default_rng(11)
    for i in range(12):
        ex, ey = rng.uniform(12, 27), rng.uniform(-2, 24)
        ez = rng.uniform(8.8, 10.2)
        sz = rng.uniform(0.22, 0.5)
        b.cuboid(f"spark_{i}", (ex, ey, ez), (ex + sz, ey + sz, ez + sz), t, uv["spark"], emission=15)
    return b.model()


# ---------------------------------------------------------------------------
# Mecha (Panzerrahmen + Energieklingen)
# ---------------------------------------------------------------------------

def paint_armor(w, h, light, dark, panel, accent):
    """Panzerplatte: Verlauf in 4 Stufen, Lichtkante oben, Fugen, Nieten, Akzentstreifen."""
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        c = lerp(light, dark, quant(y / max(1, h - 1), 4))
        if y == 0:
            c = lerp(light, (255, 255, 255), 0.45)
        if y == h - 1:
            c = panel
        img[y, :, :3] = [int(v) for v in c]
    for x in (w // 3, 2 * w // 3):
        img[1:-1, x, :3] = [int(v) for v in lerp(tuple(int(v) for v in img[2, x, :3]), panel, 0.7)]
    img[h // 2, 1:w // 3 - 1, :3] = accent
    for x in (1, w - 2):
        img[1, x, :3] = panel
    img[:, 0, :3] = img[:, -1, :3] = panel
    img[..., 3] = 255
    return Image.fromarray(img, "RGBA")


def paint_blade(w, h, core, edge, deep=None):
    """Energieklinge: heller Kern -> Energie -> dunkler Rand (5 Stufen), Lichtkante,
    Segmentfugen fuer den Mecha-Look."""
    deep = deep or lerp(edge, (0, 0, 0), 0.45)
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        t = (y + 0.5) / h
        hw = (w / 2) * (smooth(t / 0.12) if t < 0.12 else 1.0)
        if t > 0.58:
            hw *= max(0.0, 1 - (t - 0.58) / 0.42) ** 0.85
        notch = (y % 10 == 9) and 0.15 < t < 0.85
        for x in range(w):
            dx = abs(x + 0.5 - w / 2)
            if dx > hw:
                continue
            k = quant(dx / max(hw, 0.01), 5)
            if k < 0.5:
                c = lerp(core, edge, k * 2)
            else:
                c = lerp(edge, deep, (k - 0.5) * 2)
            a = int(205 + 50 * k)
            if hw - dx < 1.0:
                c, a = lerp(core, edge, 0.35), 255
            if notch:
                c = lerp(c, deep, 0.4)
            img[y, x, :3] = [int(v) for v in c]
            img[y, x, 3] = a
    return Image.fromarray(img, "RGBA")


def mecha_wing(wing_id, style, tex_dir: Path):
    atlas = Atlas("mecha", 128, 128)
    uv = {
        "armor": atlas.add("armor", paint_armor(24, 8, style["armor_light"], style["armor_dark"], style["panel"],
                                                style["accent"])),
        "joint": atlas.add("joint", paint_flat(8, 8, style["joint_light"], style["joint_dark"], outline=style["panel"])),
        "blade": atlas.add("blade", paint_blade(10, 64, style["core"], style["energy"])),
        "blade2": atlas.add("blade2", paint_blade(10, 64, lerp(style["core"], style["energy"], 0.5), style["energy"],
                                                  lerp(style["energy"], (0, 0, 0), 0.6))),
        "thrust": atlas.add("thrust", paint_glow_dot(6, (255, 255, 255), style["energy"])),
        "accent": atlas.add("accent", paint_glow_dot(6, style["core"], style["accent"])),
    }
    atlas.img.save(tex_dir / "mecha.png")

    b = ModelBuilder()
    t = b.tex("mecha", atlas.ref(wing_id))
    S, E, W = (8.6, 9.4), (11.4, 16.6), (16.2, 21.4)
    b.segment("frame_upper", S, E, 1.8, 8.1, 9.7, t, uv["armor"])
    b.segment("frame_fore", E, W, 1.6, 8.2, 9.6, t, uv["armor"])
    b.segment("frame_hand", W, (22.4, 20.6), 1.2, 8.35, 9.45, t, uv["armor"])
    # leuchtende Akzentleisten auf dem Rahmen
    b.segment("accent_upper", S, E, 0.3, 9.7, 9.78, t, uv["accent"], emission=10)
    b.segment("accent_fore", E, W, 0.3, 9.6, 9.68, t, uv["accent"], emission=10)
    for name, (px, py), sz in (("joint_s", S, 2.4), ("joint_e", E, 2.2), ("joint_w", W, 2.0)):
        b.cuboid(name, (px - sz / 2, py - sz / 2, 8.0), (px + sz / 2, py + sz / 2, 8.0 + sz), t, uv["joint"])
        b.cuboid(name + "_core", (px - 0.35, py - 0.35, 8.0 + sz), (px + 0.35, py + 0.35, 8.1 + sz), t, uv["thrust"],
                 emission=15)
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
        b.feather(f"mount_{i}", root=(rx, ry + 0.2), length=2.4, width=1.6, angle_z=ang, z=z - 0.4, tex=t,
                  uv=uv["armor"], twist=0, curl=0)
    # zweite, kuerzere Klingenreihe dahinter (zwischen den Hauptklingen) -> Tiefe + volle Silhouette
    for i in range(len(blades) - 1):
        (f0, (x0, y0), l0, a0), (f1, (x1, y1), l1, a1) = blades[i], blades[i + 1]
        f = (f0 + f1) / 2
        z = 7.85 + curl_at(2.0 + (1 - f) * 0.9) * 0.6
        b.feather(f"blade_back_{i}", root=((x0 + x1) / 2, (y0 + y1) / 2 - 1.4), length=(l0 + l1) / 2 * 0.8,
                  width=2.2, angle_z=(a0 + a1) / 2, z=z, tex=t, uv=uv["blade2"], twist=-8 * (1 - f),
                  curl=6 * (1 - f), emission=12)
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
        "vein": hexc("#ff4a1c"), "vein_core": hexc("#ffb27a"), "vein_emission": 12,
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
    # --- Membran-Varianten (gleicher Builder wie "demon", eigenes Leuchtmuster) ---
    "lava": ("membrane", {
        "pattern": "cracks", "seed": 21,
        "membrane_inner": hexc("#2e2724"), "membrane_outer": hexc("#0e0b0b"), "edge": hexc("#050404"),
        "vein": hexc("#ff5a0a"), "vein_core": hexc("#ffd34a"), "vein_emission": 15,
        "bone_light": hexc("#3a3330"), "bone_dark": hexc("#151110"),
        "claw_light": hexc("#ffb347"), "claw_dark": hexc("#b33a12"), "claw_emission": 10,
        "embers": hexc("#ff7b1c"),
    }),
    "void": ("membrane", {
        "pattern": "stars", "seed": 8,
        "membrane_inner": hexc("#2c1150"), "membrane_outer": hexc("#07020f"), "edge": hexc("#020006"),
        "vein": hexc("#ff7bf2"), "vein_core": hexc("#ffffff"), "rim_glow": hexc("#ff5fe6"), "vein_emission": 13,
        "bone_light": hexc("#3a2c52"), "bone_dark": hexc("#120c1c"),
        "claw_light": hexc("#e6ccff"), "claw_dark": hexc("#6c4a9c"),
    }),
    "frost": ("membrane", {
        "pattern": "frost", "seed": 13, "alpha": 175, "glow_radius": 1.2,
        "membrane_inner": hexc("#c6edff"), "membrane_outer": hexc("#3c7fb5"), "edge": hexc("#e9fbff"),
        "vein": hexc("#7ff3ff"), "vein_core": hexc("#ffffff"), "vein_emission": 9,
        "bone_light": hexc("#f2fcff"), "bone_dark": hexc("#8fc4e0"),
        "claw_light": hexc("#ffffff"), "claw_dark": hexc("#9fe6ff"), "claw_emission": 7,
    }),
    "plague": ("membrane", {
        "pattern": "veins", "seed": 17, "holes": True,
        "membrane_inner": hexc("#40601f"), "membrane_outer": hexc("#101a08"), "edge": hexc("#070b03"),
        "vein": hexc("#8dff3a"), "vein_core": hexc("#e6ff9a"), "vein_emission": 12,
        "bone_light": hexc("#5e5c3c"), "bone_dark": hexc("#23230f"),
        "claw_light": hexc("#d8d2a0"), "claw_dark": hexc("#77704a"),
    }),
    "bloodmoon": ("membrane", {
        "pattern": "moon", "seed": 4,
        "membrane_inner": hexc("#720b16"), "membrane_outer": hexc("#1e0206"), "edge": hexc("#0c0103"),
        "vein": hexc("#ff2a3a"), "moon": hexc("#ffe8dc"), "moon_glow": hexc("#ff3a4a"), "vein_emission": 12,
        "bone_light": hexc("#e8ebf2"), "bone_dark": hexc("#7d8494"),
        "claw_light": hexc("#ffffff"), "claw_dark": hexc("#a9b0c0"),
    }),
    "storm": ("membrane", {
        "pattern": "lightning", "seed": 29,
        "membrane_inner": hexc("#4d5668"), "membrane_outer": hexc("#161a22"), "edge": hexc("#090b10"),
        "vein": hexc("#5ab8ff"), "vein_core": hexc("#ffffff"), "vein_emission": 15,
        "bone_light": hexc("#3e4452"), "bone_dark": hexc("#171a21"),
        "claw_light": hexc("#cfe6ff"), "claw_dark": hexc("#5d7aa0"),
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
