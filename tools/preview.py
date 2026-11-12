#!/usr/bin/env python3
"""
Kleiner Software-Renderer fuer Minecraft-Item-Modelle (JSON), um Kosmetik ohne Spiel
anzusehen. Bildet nach, wie das Plugin die Fluegel darstellt:

    Modell -> ItemDisplay-Drehung (180 Grad um Y) -> Display-Transformation -> Spieler

Genutzt von generate_assets.py (Icons) und fuer Vorschaubilder:

    python3 tools/preview.py angel demon      # -> build/preview/<id>.png
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "resourcepack"


# ---------------------------------------------------------------------------
# Modell laden (Parent-Kette + Texturvariablen)
# ---------------------------------------------------------------------------

def _model_path(ref: str) -> Path:
    ns, path = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
    return PACK / "assets" / ns / "models" / f"{path}.json"


def _texture_path(ref: str) -> Path:
    ns, path = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
    return PACK / "assets" / ns / "textures" / f"{path}.png"


def load_model(ref: str) -> dict:
    data = json.loads(_model_path(ref).read_text())
    textures = {}
    elements = data.get("elements")
    if "parent" in data and not data["parent"].startswith("minecraft:"):
        parent = load_model(data["parent"])
        textures.update(parent["textures"])
        elements = elements or parent["elements"]
    textures.update(data.get("textures", {}))
    return {"textures": textures, "elements": elements or []}


def resolve_texture(textures: dict, ref: str) -> str:
    seen = 0
    while ref.startswith("#") and seen < 10:
        ref = textures.get(ref[1:], ref)
        seen += 1
    return ref


_TEX_CACHE = {}


def texture(ref: str) -> np.ndarray:
    if ref not in _TEX_CACHE:
        _TEX_CACHE[ref] = np.asarray(Image.open(_texture_path(ref)).convert("RGBA"), dtype=np.float32) / 255.0
    return _TEX_CACHE[ref]


# ---------------------------------------------------------------------------
# Geometrie wie im Spiel (CuboidModelElement / FaceBakery)
# ---------------------------------------------------------------------------

def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def element_matrix(rotation: dict) -> np.ndarray:
    if not rotation:
        return np.eye(3)
    if "axis" in rotation:
        a = math.radians(rotation["angle"])
        return {"x": rot_x, "y": rot_y, "z": rot_z}[rotation["axis"]](a)
    # 26.x: Matrix4f.rotationZYX(z, y, x) = Rz * Ry * Rx
    return rot_z(math.radians(rotation.get("z", 0))) @ rot_y(math.radians(rotation.get("y", 0))) @ rot_x(
        math.radians(rotation.get("x", 0)))


# Eckpunkte jeder Seite in Textur-Reihenfolge: (oben-links, oben-rechts, unten-rechts, unten-links)
def face_corners(face: str, f, t):
    x0, y0, z0 = f
    x1, y1, z1 = t
    return {
        "south": [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
        "north": [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
        "east": [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
        "west": [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
        "up": [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        "down": [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)],
    }[face]


def model_quads(model: dict):
    """Liefert Quads: (4 Punkte in Modell-Einheiten 0..16, 4 UVs 0..1, Textur, Leuchtstaerke)."""
    quads = []
    for el in model["elements"]:
        m = element_matrix(el.get("rotation"))
        origin = np.array(el.get("rotation", {}).get("origin", [8, 8, 8]), dtype=float)
        for face, fd in el["faces"].items():
            corners = np.array(face_corners(face, el["from"], el["to"]), dtype=float)
            corners = (corners - origin) @ m.T + origin
            u0, v0, u1, v1 = fd["uv"]
            uvs = np.array([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], dtype=float) / 16.0
            tex = resolve_texture(model["textures"], fd["texture"])
            quads.append((corners, uvs, tex, el.get("light_emission", 0)))
    return quads


# ---------------------------------------------------------------------------
# Szene: Spieler + Fluegel
# ---------------------------------------------------------------------------

def display_transform(points_model, *, side_sign, angle_deg, scale, offset, spread, attach_y=1.8):
    """Modellpunkte -> Weltpunkte, exakt wie WingInstance + ItemDisplay-Renderer."""
    p = points_model / 16.0 - 0.5
    p = p @ rot_y(math.pi).T  # ItemDisplayRenderer: rotate(Axis.YP, PI)
    p = p * scale
    p = p @ rot_y(math.radians(angle_deg) * side_sign).T
    p = p + np.array([spread, offset[0], offset[1]])
    return p + np.array([0, attach_y, 0])


def box_quads(x0, y0, z0, x1, y1, z1, color):
    quads = []
    for face in ("south", "north", "east", "west", "up", "down"):
        quads.append((np.array(face_corners(face, (x0, y0, z0), (x1, y1, z1)), dtype=float), color))
    return quads


def mannequin():
    skin, shirt, pants, hair = (0.80, 0.62, 0.48), (0.25, 0.55, 0.65), (0.22, 0.22, 0.45), (0.25, 0.17, 0.10)
    q = []
    q += box_quads(-0.25, 0.0, -0.125, 0.0, 0.75, 0.125, pants)
    q += box_quads(0.0, 0.0, -0.125, 0.25, 0.75, 0.125, pants)
    q += box_quads(-0.25, 0.75, -0.125, 0.25, 1.5, 0.125, shirt)
    q += box_quads(-0.5, 0.75, -0.125, -0.25, 1.5, 0.125, skin)
    q += box_quads(0.25, 0.75, -0.125, 0.5, 1.5, 0.125, skin)
    q += box_quads(-0.25, 1.5, -0.25, 0.25, 2.0, 0.25, skin)
    q += box_quads(-0.26, 1.85, -0.26, 0.26, 2.01, 0.26, hair)
    return q


class Renderer:
    def __init__(self, w, h, yaw_deg, pitch_deg, center, zoom, bg=(0.11, 0.10, 0.16)):
        self.w, self.h = w, h
        self.color = np.zeros((h, w, 3), dtype=np.float32) + np.array(bg, dtype=np.float32)
        self.alpha = np.zeros((h, w), dtype=np.float32)
        self.depth = np.full((h, w), np.inf, dtype=np.float32)
        self.translucent = []
        # Kamera schaut entlang +Z (also auf den Ruecken), dann um yaw/pitch gedreht
        self.view = rot_x(math.radians(pitch_deg)) @ rot_y(math.radians(yaw_deg))
        self.center = np.array(center, dtype=float)
        self.zoom = zoom
        self.light = np.array([0.35, 0.8, -0.5])
        self.light /= np.linalg.norm(self.light)

    def project(self, pts):
        v = (pts - self.center) @ self.view.T
        sx = self.w / 2 + v[:, 0] * self.zoom * -1  # Blick nach +Z: Welt +X erscheint links
        sy = self.h / 2 - v[:, 1] * self.zoom
        return np.stack([sx, sy, v[:, 2]], axis=1)

    def shade(self, pts, emission):
        if emission > 0:
            return 1.0
        n = np.cross(pts[1] - pts[0], pts[3] - pts[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            return 1.0
        n /= ln
        return 0.55 + 0.45 * abs(float(n @ self.light))

    def tri(self, P, UV, tex, shade, flat=None, defer=True):
        x0, x1 = int(max(0, math.floor(P[:, 0].min()))), int(min(self.w - 1, math.ceil(P[:, 0].max())))
        y0, y1 = int(max(0, math.floor(P[:, 1].min()))), int(min(self.h - 1, math.ceil(P[:, 1].max())))
        if x0 > x1 or y0 > y1:
            return
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay, _), (bx, by, _), (cx, cy, _) = P
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-9:
            return
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
        l3 = 1 - l1 - l2
        mask = (l1 >= -1e-4) & (l2 >= -1e-4) & (l3 >= -1e-4)
        if not mask.any():
            return
        z = l1 * P[0, 2] + l2 * P[1, 2] + l3 * P[2, 2]
        if flat is not None:
            rgba = np.zeros(xs.shape + (4,), dtype=np.float32)
            rgba[..., :3] = flat
            rgba[..., 3] = 1
        else:
            u = l1 * UV[0, 0] + l2 * UV[1, 0] + l3 * UV[2, 0]
            v = l1 * UV[0, 1] + l2 * UV[1, 1] + l3 * UV[2, 1]
            th, tw = tex.shape[:2]
            iu = np.clip((u * tw).astype(int), 0, tw - 1)
            iv = np.clip((v * th).astype(int), 0, th - 1)
            rgba = tex[iv, iu]
        a = rgba[..., 3]
        sub = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        opaque = mask & (a > 0.95) & (z < self.depth[sub])
        col = rgba[..., :3] * shade
        self.color[sub][opaque] = col[opaque]
        self.depth[sub][opaque] = z[opaque]
        self.alpha[sub][opaque] = 1
        semi = mask & (a > 0.1) & (a <= 0.95)
        if semi.any():
            self.translucent.append((sub, semi, z, col, a))

    def flush_translucent(self):
        # grob von hinten nach vorne
        self.translucent.sort(key=lambda t: -float(np.nanmean(np.where(t[1], t[2], np.nan))))
        for sub, semi, z, col, a in self.translucent:
            m = semi & (z < self.depth[sub])
            region = self.color[sub]
            region[m] = region[m] * (1 - a[m, None]) + col[m] * a[m, None]
            self.color[sub] = region
            self.alpha[sub][m] = np.maximum(self.alpha[sub][m], a[m])
        self.translucent = []

    def draw_quad(self, pts, uvs, tex, emission=0, flat=None):
        P = self.project(pts)
        s = self.shade(pts, emission)
        for idx in ((0, 1, 2), (0, 2, 3)):
            self.tri(P[list(idx)], None if uvs is None else uvs[list(idx)], tex, s, flat)

    def image(self, transparent=False):
        rgb = (np.clip(self.color, 0, 1) * 255).astype(np.uint8)
        if not transparent:
            return Image.fromarray(rgb, "RGB")
        a = (np.clip(self.alpha, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def wing_quads_world(wing_id, settings, angle_deg=None):
    out = []
    for side, model_suffix, sign, spread in (("left", "_left", -1, -settings["spread"]),
                                               ("right", "_right", 1, settings["spread"])):
        model = load_model(f"cosmetics:item/wings/{wing_id}{model_suffix}")
        for corners, uvs, tex, emission in model_quads(model):
            pts = display_transform(corners, side_sign=sign,
                                    angle_deg=settings["rest_angle"] if angle_deg is None else angle_deg,
                                    scale=settings["scale"], offset=(settings["offset_y"], settings["offset_z"]),
                                    spread=spread)
            out.append((pts, uvs, texture(tex), emission))
    return out


DEFAULT_SETTINGS = {"scale": 0.8, "offset_y": -0.42, "offset_z": -0.2, "spread": 0.06, "rest_angle": 20}


def render_view(wing_id, yaw, pitch, size=420, zoom=125, settings=None, with_player=True, angle=None,
                center=(0, 1.3, 0), transparent=False):
    settings = settings or DEFAULT_SETTINGS
    r = Renderer(size, size, yaw, pitch, center, zoom)
    if with_player:
        for pts, col in mannequin():
            r.draw_quad(pts, None, None, flat=np.array(col) * 1.0)
    for pts, uvs, tex, em in wing_quads_world(wing_id, settings, angle):
        r.draw_quad(pts, uvs, tex, em)
    r.flush_translucent()
    return r.image(transparent)


def contact_sheet(wing_id, settings=None) -> Image.Image:
    views = [
        ("Ruecken", 0, 8),
        ("Schraeg", 35, 12),
        ("Seite", 90, 5),
        ("Vorne", 180, 5),
    ]
    imgs = [render_view(wing_id, yaw, pitch, settings=settings) for _, yaw, pitch in views]
    flap = render_view(wing_id, 35, 12, settings=settings,
                       angle=(settings or DEFAULT_SETTINGS)["rest_angle"] + 30)
    imgs.append(flap)
    w = sum(i.width for i in imgs)
    sheet = Image.new("RGB", (w, imgs[0].height), (20, 20, 30))
    x = 0
    for img in imgs:
        sheet.paste(img, (x, 0))
        x += img.width
    return sheet


def main(ids):
    out = ROOT / "build" / "preview"
    out.mkdir(parents=True, exist_ok=True)
    for wid in ids:
        sheet = contact_sheet(wid)
        sheet.save(out / f"{wid}.png")
        print(out / f"{wid}.png")


if __name__ == "__main__":
    main(sys.argv[1:] or ["angel"])
