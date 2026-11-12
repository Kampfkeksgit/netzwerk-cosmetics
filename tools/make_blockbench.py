#!/usr/bin/env python3
"""Erzeugt blockbench/wings.bbmodel: EIN Blockbench-Projekt mit allen Fluegeln.

Jeder Fluegel ist eine eigene Gruppe (linke Seite, die rechte entsteht per wings.mirror),
darunter Untergruppen je Lage (primary, covert, bone ...). Alle Fluegel liegen an derselben
Stelle (Wurzel bei 8,8,8) - sichtbar ist nur der erste, die anderen blendet man im Outliner
mit dem Auge ein. Texturen sind eingebettet.

Das Projekt ist eine ANSICHT der generierten Modelle; Quelle bleibt tools/wings.py.
Wird von generate_assets.py automatisch mit erzeugt.
"""
import base64
import json
import re
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
NS = ROOT / "resourcepack" / "assets" / "cosmetics"
OUT = ROOT / "blockbench" / "wings.bbmodel"
FACES = ("north", "east", "south", "west", "up", "down")
_UUID_NS = uuid.UUID("6f1d2c1e-0a54-4c58-9b53-6e0f0d3c7a11")


def uid(*parts) -> str:
    """Stabile UUIDs -> gleiche Eingabe ergibt dieselbe Datei (saubere Git-Diffs)."""
    return str(uuid.uuid5(_UUID_NS, "/".join(parts)))


def rotation_of(el):
    r = el.get("rotation")
    if not r:
        return [0, 0, 0], [8, 8, 8]
    if "axis" in r:
        rot = [r["angle"] if a == r["axis"] else 0 for a in "xyz"]
    else:
        rot = [r.get("x", 0), r.get("y", 0), r.get("z", 0)]
    return rot, list(r["origin"])


def layer_of(name: str) -> str:
    """primary_3 -> primary, primary_3_glow -> primary_glow, finger_0_a -> finger"""
    glow = name.endswith("_glow")
    base = re.sub(r"_glow$", "", name)
    base = re.sub(r"(_\d+)(_[a-z]+)?$", "", base)
    return base + ("_glow" if glow else "")


def group(name, gid, children, visible, is_open=False):
    meta = {"name": name, "uuid": gid, "export": True, "locked": False, "scope": 0, "selected": False,
            "visibility": visible, "origin": [8, 8, 8], "rotation": [0, 0, 0], "color": 0, "children": [],
            "reset": False, "shade": True, "mirror_uv": False, "autouv": 0, "isOpen": is_open,
            "primary_selected": False}
    return meta, {"uuid": gid, "isOpen": is_open, "children": children}


def build(wing_ids) -> dict:
    elements, groups, outliner, textures = [], [], [], []
    for n, wid in enumerate(wing_ids):
        visible = n == 0
        model = json.loads((NS / "models" / "item" / "wings" / f"{wid}_left.json").read_text())
        tex_index = {}
        for key, ref in model["textures"].items():
            if key == "particle":
                continue
            rel = ref.split(":", 1)[1]
            png = NS / "textures" / (rel + ".png")
            w, h = Image.open(png).size
            tex_index["#" + key] = len(textures)
            textures.append({
                "name": f"{wid}_{key}.png", "folder": str(Path(rel).parent).replace("\\", "/"),
                "namespace": "cosmetics", "id": f"{wid}_{key}", "group": "", "scope": 0,
                "width": w, "height": h, "uv_width": 16, "uv_height": 16, "particle": False,
                "use_as_default": False, "layers_enabled": False, "sync_to_project": "", "file_format": "png",
                "render_mode": "default", "render_sides": "auto", "wrap_mode": "limited", "pbr_channel": "color",
                "fps": 7, "force_translucent": False, "frame_time": 1, "frame_order_type": "loop",
                "frame_order": "", "frame_interpolate": False, "visible": True, "internal": True, "saved": True,
                "uuid": uid(wid, "tex", key),
                "source": "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode(),
            })
        layers = {}
        for i, el in enumerate(model["elements"]):
            rot, origin = rotation_of(el)
            faces = {}
            for f in FACES:
                fd = el["faces"].get(f)
                faces[f] = ({"uv": fd["uv"], "texture": tex_index[fd["texture"]]} if fd
                            else {"uv": [0, 0, 0, 0], "texture": None})
            eid = uid(wid, "el", str(i), el["name"])
            elements.append({
                "name": el["name"], "box_uv": False, "render_order": "default", "rescale": False, "locked": False,
                "shade_direction_override": "", "light_emission": el.get("light_emission", 0), "export": True,
                "scope": 0, "allow_mirror_modeling": True, "visibility": visible,
                "from": el["from"], "to": el["to"], "autouv": 0, "color": n % 8,
                "rotation": rot, "origin": origin, "faces": faces, "type": "cube", "uuid": eid,
            })
            layers.setdefault(layer_of(el["name"]), []).append(eid)
        children = []
        for lname, ids in layers.items():
            meta, node = group(lname, uid(wid, "group", lname), ids, visible)
            groups.append(meta)
            children.append(node)
        meta, node = group(wid, uid(wid, "wing"), children, visible, is_open=visible)
        groups.append(meta)
        outliner.append(node)
    return {
        "meta": {"format_version": "5.0", "model_format": "java_block", "box_uv": False},
        "name": "wings", "parent": "", "java_block_version": "26.3", "ambientocclusion": True,
        "front_gui_light": False, "visible_box": [1, 1, 0], "variable_placeholders": "",
        "multi_file_ruleset": "", "variable_placeholder_buttons": [], "unhandled_root_fields": {},
        "resolution": {"width": 16, "height": 16},
        "elements": elements, "groups": groups, "outliner": outliner, "textures": textures,
    }


def main(wing_ids=None) -> Path:
    if wing_ids is None:
        import wings
        wing_ids = list(wings.WINGS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(wing_ids), separators=(",", ":")) + "\n")
    return OUT


if __name__ == "__main__":
    print(main())
