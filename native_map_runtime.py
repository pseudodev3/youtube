from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

W, H = 1080, 1920
_BINARY = Path(__file__).resolve().parent / "cpp" / "map_engine"
_CACHE: dict[tuple[str, int, int, int], dict[str, Any] | None] = {}
_WARNED: set[str] = set()


def is_available() -> bool:
    return _BINARY.exists() and os.access(_BINARY, os.X_OK)


def _warn_once(key: str, message: str) -> None:
    if key not in _WARNED:
        _WARNED.add(key)
        print(f"GRIDLOOP native map fallback: {message}")


def _parse_rgb(text: str, alpha: int = 255) -> tuple[int, int, int, int]:
    vals = [int(v) for v in text.split(",")]
    if len(vals) >= 4:
        return vals[0], vals[1], vals[2], vals[3]
    return vals[0], vals[1], vals[2], alpha


def _scene(track: str, episode: int) -> dict[str, Any] | None:
    fps = int(os.getenv("FPS", "30"))
    frames = max(1, int(float(os.getenv("DURATION", "24")) * fps) + 8)
    key = (track, int(episode), frames, fps)
    if key in _CACHE:
        return _CACHE[key]
    if not is_available():
        _CACHE[key] = None
        return None

    # Episode is intentionally part of the seed: a return to the same road can
    # have slightly different natural detail without changing its visual identity.
    seed = max(1, int(episode) * 10007 + 7919)
    try:
        proc = subprocess.run(
            [str(_BINARY), track, str(seed), str(frames), str(fps)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        _warn_once(track, f"{track}: {exc}")
        _CACHE[key] = None
        return None

    scene: dict[str, Any] = {
        "sky_top": (100, 160, 210, 255),
        "sky_bottom": (190, 215, 230, 255),
        "ground": (80, 130, 75, 255),
        "terrain": [],
        "objects": {},
    }
    try:
        for raw in proc.stdout.splitlines():
            if not raw:
                continue
            parts = raw.split("|")
            tag = parts[0]
            if tag == "S" and len(parts) >= 3:
                scene["sky_top"] = _parse_rgb(parts[1])
                scene["sky_bottom"] = _parse_rgb(parts[2])
            elif tag == "G" and len(parts) >= 2:
                scene["ground"] = _parse_rgb(parts[1])
            elif tag == "P" and len(parts) >= 3:
                color = _parse_rgb(parts[1])
                points = []
                for pair in parts[2].split(";"):
                    xs, ys = pair.split(",", 1)
                    points.append((float(xs), float(ys)))
                if len(points) >= 3:
                    scene["terrain"].append((color, points))
            elif tag == "O" and len(parts) >= 7:
                frame_no = int(parts[1])
                obj = {
                    "kind": parts[2],
                    "x": float(parts[3]),
                    "y": float(parts[4]),
                    "scale": float(parts[5]),
                    "variant": int(parts[6]),
                }
                scene["objects"].setdefault(frame_no, []).append(obj)
    except Exception as exc:
        _warn_once(track + "-parse", f"could not parse {track} scene: {exc}")
        _CACHE[key] = None
        return None

    _CACHE[key] = scene
    return scene


def has_scene(track: str, episode: int) -> bool:
    return _scene(track, episode) is not None


def draw_horizon(draw: ImageDraw.ImageDraw, track: str, episode: int) -> bool:
    scene = _scene(track, episode)
    if scene is None:
        return False
    top = scene["sky_top"]
    bottom = scene["sky_bottom"]
    for y in range(0, 620, 10):
        t = y / 620.0
        c = tuple(int(top[i] * (1.0 - t) + bottom[i] * t) for i in range(3))
        draw.rectangle([0, y, W, y + 10], fill=c + (255,))
    for color, pts in scene["terrain"]:
        draw.polygon(pts, fill=color)

    # Lightweight atmospheric perspective: distinct per biome, behind the race.
    if track == "country":
        draw.rectangle([0, 525, W, 650], fill=(244, 218, 160, 24))
    elif track == "mountain":
        draw.rectangle([0, 500, W, 675], fill=(190, 205, 211, 28))
    elif track == "rain":
        draw.rectangle([0, 450, W, 690], fill=(145, 160, 166, 34))
    elif track == "snow":
        draw.rectangle([0, 470, W, 700], fill=(229, 239, 243, 30))
    elif track == "street":
        draw.rectangle([0, 440, W, 650], fill=(151, 157, 164, 18))
    elif track == "night_city":
        draw.rectangle([0, 455, W, 665], fill=(72, 83, 113, 18))
    elif track == "neon_rain":
        draw.rectangle([0, 430, W, 675], fill=(104, 66, 139, 26))
    elif track == "alpine":
        draw.rectangle([0, 445, W, 705], fill=(207, 225, 234, 30))
    elif track in {"canyon", "extreme_canyon"}:
        alpha = 34 if track == "extreme_canyon" else 24
        draw.rectangle([0, 510, W, 690], fill=(236, 165, 111, alpha))
    return True


def draw_ground(draw: ImageDraw.ImageDraw, track: str, episode: int) -> bool:
    scene = _scene(track, episode)
    if scene is None:
        return False
    draw.rectangle([0, 600, W, H], fill=scene["ground"])
    # Terrain is redrawn after the ground plane. The actual race road is rendered
    # later by renderer.py, so this remains safely behind cars and track markings.
    for color, pts in scene["terrain"]:
        draw.polygon(pts, fill=color)
    return True


def _tree(d: ImageDraw.ImageDraw, x: float, y: float, s: float, dark: bool = False) -> None:
    trunk = (70, 50, 34, 245) if not dark else (42, 34, 29, 250)
    leaf1 = (49, 112, 55, 248) if not dark else (24, 66, 39, 250)
    leaf2 = (76, 145, 67, 235) if not dark else (34, 83, 47, 242)
    d.rectangle([x-5*s, y-66*s, x+5*s, y], fill=trunk)
    d.ellipse([x-34*s, y-116*s, x+34*s, y-49*s], fill=leaf1)
    d.ellipse([x-27*s, y-142*s, x+28*s, y-78*s], fill=leaf2)


def _pine(d: ImageDraw.ImageDraw, x: float, y: float, s: float, snowy: bool = False) -> None:
    d.rectangle([x-4*s, y-58*s, x+4*s, y], fill=(63,48,36,245))
    for n, width in enumerate((38,31,24)):
        cy = y - (43+n*24)*s
        d.polygon([(x,cy-39*s),(x-width*s,cy+17*s),(x+width*s,cy+17*s)], fill=(31,78,49,248))
        if snowy:
            d.line([(x-width*.68*s,cy+5*s),(x+width*.68*s,cy+5*s)], fill=(239,246,249,225), width=max(2,int(4*s)))


_OBJECT_HALF_WIDTH = {
    "tree": 38, "tree_dark": 40, "pine": 38, "pine_snow": 40,
    "fence": 36, "hedge": 44, "utility_pole": 28, "signboard": 38,
    "rock": 32, "cactus": 28, "barrier": 42, "guardrail": 42,
    "bollard": 8, "lamp": 30, "tunnel_light": 30, "warning": 28,
    "snowbank": 42, "palm": 44, "neon": 31,
    "floodlight": 34, "haybale": 34, "scrub": 30,
    "streetlight": 38, "reflector": 9, "snowpole": 10,
    "city_sign": 38, "vent": 34,
}


def _road_safe_pose(frame, obj: dict[str, Any]) -> tuple[float, float]:
    """Project a native prop using the same perspective depth as the live road."""
    if frame is None:
        return float(obj["x"]), float(obj["y"])

    side = -1.0 if float(obj["x"]) < W / 2 else 1.0

    # C++ encodes perspective depth into scale as 0.28 + p*1.15. Recovering p
    # from scale is exact and avoids mixing the old roadside y projection with
    # renderer.py's road projection.
    scale = float(obj.get("scale", 1.0))
    p = max(0.0, min(1.0, (scale - 0.28) / 1.15))

    shake = float(getattr(frame, "shake", 0.0))
    horizon = 600.0 + shake * 1.2
    projected_y = horizon + (p ** 1.72) * (H - horizon)

    road_curve = float(getattr(frame, "road_curve", 0.0))
    road_curve_far = float(getattr(frame, "road_curve_far", 0.0))
    t = float(getattr(frame, "t", 0.0))
    heading = float(getattr(getattr(frame, "player", None), "heading", 0.0))
    center = (
        W / 2
        + road_curve * (p ** 1.62) * 700
        + road_curve_far * math.sin(p * math.pi) * 300
        + math.sin(t * 0.14 + p * 3.0) * 50 * p
        + heading * 18
    )

    width_mul = float(getattr(frame, "road_width", 0.82)) / 0.82
    half_road = (65 + (p ** 1.28) * 980) * width_mul
    shoulder = 28 + p * 30
    radius = _OBJECT_HALF_WIDTH.get(str(obj.get("kind")), 30) * scale

    # Near-camera props get more breathing room. A baseline 30px also absorbs
    # camera punch from collisions that is intentionally not part of map data.
    safety = 30 + 30 * p
    jitter = (int(obj.get("variant", 0)) % 3) * 9 * scale
    projected_x = center + side * (half_road + shoulder + radius + safety + jitter)
    return projected_x, projected_y


def _draw_object(d: ImageDraw.ImageDraw, obj: dict[str, Any]) -> None:
    kind = obj["kind"]
    x, y, s = obj["x"], obj["y"], obj["scale"]
    v = int(obj["variant"])
    if kind == "tree":
        _tree(d,x,y,s*.70)
    elif kind == "tree_dark":
        _tree(d,x,y,s*.72,True)
    elif kind == "pine":
        _pine(d,x,y,s*.74,False)
    elif kind == "pine_snow":
        _pine(d,x,y,s*.76,True)
    elif kind == "fence":
        wood = (80+v*5,56+v*3,34,245)
        d.rounded_rectangle([x-2.3*s,y-42*s,x+2.3*s,y+3*s],radius=max(1,int(1.5*s)),fill=wood)
        d.line([(x-34*s,y-29*s),(x+34*s,y-29*s)],fill=(116,80,45,220),width=max(2,int(2.2*s)))
        d.line([(x-34*s,y-14*s),(x+34*s,y-14*s)],fill=(142,99,56,205),width=max(2,int(1.8*s)))
    elif kind == "hedge":
        # Low, dense rural hedge. Keep it visually separate from full trees.
        dark = (67,91+v*2,45,238)
        light = (92,113+v*2,54,220)
        d.rounded_rectangle([x-42*s,y-34*s,x+42*s,y+4*s],radius=max(3,int(10*s)),fill=dark)
        d.ellipse([x-35*s,y-48*s,x-1*s,y-12*s],fill=light)
        d.ellipse([x-4*s,y-50*s,x+34*s,y-10*s],fill=light)
    elif kind == "utility_pole":
        wood = (82,61,43,245)
        wire = (55,54,51,190)
        d.rectangle([x-3.5*s,y-112*s,x+3.5*s,y],fill=wood)
        d.line([(x-25*s,y-96*s),(x+25*s,y-96*s)],fill=wood,width=max(2,int(4*s)))
        d.ellipse([x-19*s,y-101*s,x-13*s,y-95*s],fill=(218,214,190,220))
        d.ellipse([x+13*s,y-101*s,x+19*s,y-95*s],fill=(218,214,190,220))
        side = 1 if x < W/2 else -1
        d.line([(x+side*18*s,y-98*s),(x+side*62*s,y-88*s)],fill=wire,width=max(1,int(1.5*s)))
    elif kind == "signboard":
        post = (67,72,75,242)
        panel = (226,229,225,242)
        accent = (206,61,52,235)
        d.rectangle([x-3*s,y-64*s,x+3*s,y],fill=post)
        d.rounded_rectangle([x-34*s,y-92*s,x+34*s,y-58*s],radius=max(2,int(4*s)),fill=panel)
        d.rectangle([x-29*s,y-86*s,x+29*s,y-79*s],fill=accent)
        d.rectangle([x-23*s,y-73*s,x+16*s,y-68*s],fill=(84,90,94,210))
    elif kind == "rock":
        shade=(99+v*7,88+v*5,76+v*3,238)
        d.polygon([(x-27*s,y),(x-18*s,y-28*s),(x+7*s,y-38*s),(x+30*s,y-9*s),(x+20*s,y+4*s)],fill=shade)
    elif kind == "cactus":
        green=(57,105+v*3,64,242)
        d.rounded_rectangle([x-5*s,y-75*s,x+5*s,y],radius=max(2,int(4*s)),fill=green)
        d.line([(x-3*s,y-52*s),(x-23*s,y-52*s),(x-23*s,y-68*s)],fill=green,width=max(3,int(8*s)))
        d.line([(x+3*s,y-39*s),(x+22*s,y-39*s),(x+22*s,y-57*s)],fill=green,width=max(3,int(8*s)))
    elif kind in {"barrier","guardrail"}:
        c=(206,209,204,235) if kind=="guardrail" else (220,218,205,238)
        d.rounded_rectangle([x-38*s,y-7*s,x+38*s,y+6*s],radius=max(2,int(3*s)),fill=c)
        if kind=="barrier":
            d.rectangle([x-34*s,y-4*s,x-8*s,y+3*s],fill=(213,57,51,225))
            d.rectangle([x+8*s,y-4*s,x+34*s,y+3*s],fill=(213,57,51,225))
    elif kind == "bollard":
        d.rounded_rectangle([x-5*s,y-37*s,x+5*s,y+2*s],radius=max(2,int(3*s)),fill=(230,226,211,238))
        d.rectangle([x-5*s,y-27*s,x+5*s,y-20*s],fill=(216,65,54,230))
    elif kind in {"lamp","tunnel_light"}:
        pole=(39,44,51,242)
        d.rectangle([x-3*s,y-82*s,x+3*s,y],fill=pole)
        if kind=="lamp":
            d.line([(x,y-79*s),(x+(22 if x<W/2 else -22)*s,y-79*s)],fill=pole,width=max(2,int(4*s)))
            lx=x+(22 if x<W/2 else -22)*s
            d.ellipse([lx-8*s,y-86*s,lx+8*s,y-72*s],fill=(255,218,126,215))
        else:
            d.rounded_rectangle([x-24*s,y-88*s,x+24*s,y-78*s],radius=max(2,int(3*s)),fill=(246,226,168,220))
    elif kind == "streetlight":
        pole=(37,42,48,245)
        inward = 1 if x < W/2 else -1
        lx=x+inward*30*s
        ly=y-104*s
        # Warm halo first, then the actual fixture so the light reads at phone size.
        d.ellipse([lx-30*s,ly-25*s,lx+30*s,ly+25*s],fill=(255,209,116,42))
        d.ellipse([lx-17*s,ly-14*s,lx+17*s,ly+14*s],fill=(255,220,139,68))
        d.rectangle([x-3*s,y-101*s,x+3*s,y],fill=pole)
        d.line([(x,y-98*s),(lx,ly)],fill=pole,width=max(2,int(4*s)))
        d.rounded_rectangle([lx-10*s,ly-5*s,lx+10*s,ly+5*s],radius=max(1,int(2*s)),fill=(255,226,153,238))
        d.ellipse([lx-42*s,y-5*s,lx+42*s,y+12*s],fill=(255,205,112,20))
    elif kind == "reflector":
        d.rectangle([x-3*s,y-42*s,x+3*s,y],fill=(212,216,211,238))
        d.rectangle([x-5*s,y-35*s,x+5*s,y-27*s],fill=(245,244,222,235))
        d.ellipse([x-8*s,y-39*s,x+8*s,y-23*s],fill=(210,235,255,36))
    elif kind == "snowpole":
        d.rectangle([x-3*s,y-75*s,x+3*s,y],fill=(225,230,230,245))
        d.rectangle([x-4*s,y-68*s,x+4*s,y-54*s],fill=(219,63,56,235))
        d.rectangle([x-4*s,y-42*s,x+4*s,y-28*s],fill=(219,63,56,235))
    elif kind == "city_sign":
        pole=(52,57,63,240)
        panel=(48,59+v*5,70+v*3,242)
        d.rectangle([x-3*s,y-72*s,x+3*s,y],fill=pole)
        d.rounded_rectangle([x-36*s,y-102*s,x+36*s,y-69*s],radius=max(2,int(5*s)),fill=panel)
        d.rectangle([x-27*s,y-94*s,x+23*s,y-88*s],fill=(221,224,217,210))
        d.rectangle([x-27*s,y-82*s,x+10*s,y-77*s],fill=(157,196,219,180))
    elif kind == "vent":
        metal=(66,69,73,238)
        d.rounded_rectangle([x-30*s,y-52*s,x+30*s,y+3*s],radius=max(2,int(5*s)),fill=metal)
        for yy in range(4):
            y0=y-(42-yy*10)*s
            d.line([(x-22*s,y0),(x+22*s,y0)],fill=(31,34,38,220),width=max(1,int(2*s)))
    elif kind == "warning":
        d.rectangle([x-3*s,y-58*s,x+3*s,y],fill=(60,54,46,240))
        d.polygon([(x,y-82*s),(x-24*s,y-47*s),(x+24*s,y-47*s)],fill=(255,207,57,240))
        d.polygon([(x,y-72*s),(x-12*s,y-52*s),(x+12*s,y-52*s)],fill=(43,39,34,220))
    elif kind == "floodlight":
        pole=(64,69,72,242)
        d.rectangle([x-3*s,y-118*s,x+3*s,y],fill=pole)
        d.line([(x-24*s,y-112*s),(x+24*s,y-112*s)],fill=pole,width=max(2,int(4*s)))
        for dx in (-18,-6,6,18):
            d.rounded_rectangle([x+(dx-5)*s,y-121*s,x+(dx+5)*s,y-111*s],radius=max(1,int(2*s)),fill=(243,238,204,230))
    elif kind == "haybale":
        straw=(201,163+v*3,73,240)
        edge=(139,108,52,220)
        d.rounded_rectangle([x-28*s,y-34*s,x+28*s,y+3*s],radius=max(3,int(8*s)),fill=straw,outline=edge,width=max(1,int(2*s)))
        d.line([(x-6*s,y-33*s),(x-6*s,y+2*s)],fill=edge,width=max(1,int(2*s)))
        d.line([(x+8*s,y-33*s),(x+8*s,y+2*s)],fill=edge,width=max(1,int(2*s)))
    elif kind == "scrub":
        dark=(92,92,47,235)
        light=(125,117,59,215)
        d.ellipse([x-29*s,y-25*s,x+10*s,y+4*s],fill=dark)
        d.ellipse([x-7*s,y-33*s,x+28*s,y+3*s],fill=light)
        d.ellipse([x-15*s,y-40*s,x+12*s,y-6*s],fill=(111,106,52,220))
    elif kind == "snowbank":
        d.ellipse([x-38*s,y-22*s,x+40*s,y+7*s],fill=(239,246,249,222))
    elif kind == "palm":
        d.line([(x,y),(x+5*s,y-94*s)],fill=(102,72,44,245),width=max(3,int(7*s)))
        top=(x+5*s,y-94*s)
        for dx,dy in ((-42,-12),(42,-12),(-32,12),(32,12),(0,-34)):
            d.line([top,(top[0]+dx*s,top[1]+dy*s)],fill=(47,117,68,238),width=max(3,int(6*s)))
    elif kind == "neon":
        glow=(51,228,255,220) if v%2 else (255,61,211,220)
        d.rectangle([x-28*s,y-55*s,x+28*s,y-42*s],fill=glow)
        d.rectangle([x-3*s,y-42*s,x+3*s,y],fill=(41,45,53,230))
    else:
        d.ellipse([x-7*s,y-7*s,x+7*s,y+7*s],fill=(235,215,130,210))


def draw_roadside(
    img: Image.Image,
    track: str,
    episode: int,
    frame_no: int,
    frame=None,
) -> bool:
    scene = _scene(track, episode)
    if scene is None:
        return False
    objects = scene["objects"].get(int(frame_no), ())
    if not objects:
        return True
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer, "RGBA")
    # Farther objects first, nearer objects last, which gives natural depth.
    for original in sorted(objects, key=lambda x: x["y"]):
        obj = dict(original)
        obj["x"], obj["y"] = _road_safe_pose(frame, obj)
        s = float(obj.get("scale", 1.0))
        if obj["x"] < -140 * s or obj["x"] > W + 140 * s:
            continue
        _draw_object(d, obj)
    img.paste(layer, (0,0), layer)
    return True
