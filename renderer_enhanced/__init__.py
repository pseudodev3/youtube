from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import ImageDraw

# Load the existing enhanced renderer implementation from the sibling module file.
_base_path = Path(__file__).resolve().parent.parent / "renderer_enhanced.py"
_spec = importlib.util.spec_from_file_location("_gridloop_renderer_enhanced_base", _base_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load GRIDLOOP renderer from {_base_path}")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

W = _base.W
H = _base.H

_GENERIC_MOUNTAINS = [
    (0,610),(120,500),(235,585),(360,455),(480,565),
    (620,430),(760,555),(900,470),(1080,585),(1080,760),(0,760),
]
_WORLD_STATE = {"key": "training", "phase": "done"}


def _road_key(frame) -> str:
    name = str(getattr(frame, "track_name", ""))
    prefixes = {
        "Training Circuit": "training",
        "Country Roads": "country",
        "Mountain Pass": "mountain",
        "Night City": "night_city",
        "Wet Circuit": "rain",
        "Coastal Road": "coast",
        "Snow Pass": "snow",
        "Canyon Run": "canyon",
        "Desert Highway": "desert",
        "Forest Sprint": "forest",
        "Street Circuit": "street",
        "Tunnel City": "tunnel",
        "Neon Rain": "neon_rain",
        "Alpine Pass": "alpine",
        "Extreme Canyon": "extreme_canyon",
    }
    for prefix, key in prefixes.items():
        if name.startswith(prefix):
            return key
    return str(getattr(frame, "track_theme", "training"))


def _sky_gradient(d, top, bottom) -> None:
    for y in range(0, 620, 10):
        t = y / 620.0
        c = tuple(int(top[i] * (1.0 - t) + bottom[i] * t) for i in range(3))
        d.rectangle([0, y, W, y + 10], fill=c + (255,))


def _world_horizon(d, key: str) -> None:
    """Replace the old universal mountain silhouette with a location-specific horizon."""
    if key == "training":
        _sky_gradient(d, (92, 160, 218), (171, 210, 233))
        d.polygon([(0,610),(145,548),(285,596),(450,548),(620,602),(780,555),(930,600),(1080,558),(1080,760),(0,760)], fill=(84,143,79,255))
        for x in (45, 865):
            d.rectangle([x,500,x+170,600], fill=(87,92,98,235))
            for yy in range(518,590,18):
                d.line([(x+8,yy),(x+160,yy)], fill=(223,225,221,150), width=3)

    elif key == "country":
        _sky_gradient(d, (132, 193, 231), (207, 227, 215))
        d.polygon([(0,626),(125,574),(250,616),(380,558),(515,617),(650,571),(795,622),(940,576),(1080,616),(1080,780),(0,780)], fill=(98,151,76,255))
        d.polygon([(0,668),(200,617),(405,681),(605,625),(805,687),(1080,630),(1080,820),(0,820)], fill=(139,174,84,255))
        d.rectangle([94,554,176,616], fill=(151,74,49,245))
        d.polygon([(80,554),(135,518),(191,554)], fill=(92,51,39,245))
        d.rectangle([196,548,218,616], fill=(193,198,180,235))
        d.ellipse([193,533,221,561], fill=(211,216,199,235))

    elif key == "mountain":
        _sky_gradient(d, (104, 156, 203), (187, 205, 217))
        d.polygon([(0,690),(100,470),(210,610),(330,350),(455,640),(590,405),(720,615),(850,315),(980,590),(1080,425),(1080,820),(0,820)], fill=(65,77,84,255))
        d.polygon([(0,725),(175,560),(315,705),(500,475),(655,710),(820,515),(1080,690),(1080,850),(0,850)], fill=(103,114,117,245))
        for x,y in ((330,350),(590,405),(850,315)):
            d.polygon([(x,y),(x-48,y+92),(x+8,y+68),(x+58,y+98)], fill=(223,229,231,220))

    elif key == "night_city":
        _sky_gradient(d, (14, 22, 47), (44, 52, 73))
        d.rectangle([0,605,W,790], fill=(23,28,38,255))
        for i,x in enumerate(range(0,W,90)):
            h = 125 + (i % 4) * 56
            d.rectangle([x,605-h,x+66,605], fill=(18,23,33,248))
            for yy in range(605-h+18,590,28):
                d.rectangle([x+11,yy,x+19,yy+8], fill=(255,211,91,180))
                d.rectangle([x+38,yy,x+46,yy+8], fill=(92,178,255,145))

    elif key == "rain":
        _sky_gradient(d, (58,76,95), (113,129,139))
        d.rectangle([0,607,W,780], fill=(57,77,68,255))
        for x in range(-20,W,86):
            d.ellipse([x,515,x+110,625], fill=(50,70,61,235))

    elif key == "coast":
        _sky_gradient(d, (89, 181, 232), (204, 226, 236))
        d.rectangle([0,548,W,760], fill=(42,143,193,255))
        for yy in range(580,745,35):
            d.line([(0,yy),(W,yy)], fill=(207,238,247,60), width=3)
        d.ellipse([825,250,930,355], fill=(255,219,111,238))
        d.polygon([(0,650),(135,560),(220,650),(155,785),(0,830)], fill=(101,103,91,255))
        d.polygon([(1080,650),(945,555),(860,655),(925,790),(1080,835)], fill=(95,99,88,255))

    elif key == "snow":
        _sky_gradient(d, (169,202,229), (230,239,244))
        d.polygon([(0,700),(120,495),(220,635),(355,420),(510,680),(660,465),(820,660),(950,440),(1080,640),(1080,820),(0,820)], fill=(204,217,224,255))
        d.polygon([(0,735),(190,590),(350,730),(560,560),(760,735),(940,585),(1080,710),(1080,840),(0,840)], fill=(240,245,247,248))

    elif key == "canyon":
        _sky_gradient(d, (204,141,98), (238,185,124))
        d.polygon([(0,245),(150,325),(110,555),(190,675),(125,830),(0,900)], fill=(126,68,47,255))
        d.polygon([(1080,235),(930,315),(970,550),(890,670),(955,830),(1080,905)], fill=(113,61,45,255))
        d.polygon([(230,610),(355,470),(455,610)], fill=(155,83,51,235))
        d.polygon([(625,610),(760,445),(875,610)], fill=(143,75,49,230))

    elif key == "desert":
        _sky_gradient(d, (229,177,109), (247,214,151))
        d.ellipse([815,230,935,350], fill=(255,223,108,240))
        d.polygon([(0,655),(190,580),(340,650),(500,600),(690,675),(870,590),(1080,660),(1080,820),(0,820)], fill=(211,163,91,255))
        d.polygon([(0,720),(245,645),(470,735),(700,660),(900,725),(1080,675),(1080,850),(0,850)], fill=(231,185,108,250))

    elif key == "forest":
        _sky_gradient(d, (72,121,116), (137,157,138))
        for x in range(-20,W+40,62):
            h = 120 + ((x // 62) % 3) * 35
            d.rectangle([x+24,580-h,x+34,615], fill=(52,44,34,248))
            d.polygon([(x+29,580-h-95),(x-12,580-h+10),(x+70,580-h+10)], fill=(30,70,44,252))
            d.polygon([(x+29,580-h-55),(x-6,580-h+45),(x+64,580-h+45)], fill=(35,82,49,248))

    elif key == "street":
        _sky_gradient(d, (97,118,142), (165,178,188))
        for xs in (range(0,315,72), range(765,1080,72)):
            for i,x in enumerate(xs):
                h = 170 + (i % 3) * 66
                d.rectangle([x,610-h,x+62,615], fill=(61,65,72,248))
                for yy in range(610-h+22,595,32):
                    d.rectangle([x+10,yy,x+19,yy+10], fill=(231,214,146,145))

    elif key == "tunnel":
        d.rectangle([0,0,W,620], fill=(25,28,34,255))
        d.polygon([(0,0),(W,0),(925,555),(155,555)], fill=(14,17,22,255))
        d.rectangle([0,545,W,620], fill=(38,41,46,255))
        for x in range(130,950,135):
            d.rectangle([x,245,x+74,258], fill=(246,224,166,215))

    elif key == "neon_rain":
        _sky_gradient(d, (28,19,57), (63,41,83))
        for i,x in enumerate(range(0,W,87)):
            h = 135 + (i % 4) * 56
            d.rectangle([x,610-h,x+64,615], fill=(16,19,30,250))
            glow = (48,224,255,205) if i % 2 else (255,61,210,205)
            d.rectangle([x+9,610-h+24,x+48,610-h+33], fill=glow)

    elif key == "alpine":
        _sky_gradient(d, (141,185,222), (222,235,242))
        d.polygon([(0,720),(115,450),(220,630),(360,290),(500,680),(650,385),(790,650),(930,260),(1080,625),(1080,830),(0,830)], fill=(133,156,169,255))
        for x,y in ((360,290),(650,385),(930,260)):
            d.polygon([(x,y),(x-74,y+150),(x,y+108),(x+78,y+155)], fill=(243,248,250,242))

    elif key == "extreme_canyon":
        _sky_gradient(d, (168,85,64), (215,125,82))
        d.polygon([(0,110),(245,205),(180,425),(270,615),(190,850),(0,980)], fill=(90,42,38,255))
        d.polygon([(1080,100),(835,200),(900,420),(810,610),(890,850),(1080,990)], fill=(81,38,36,255))
        d.polygon([(315,610),(425,465),(510,610)], fill=(116,55,43,242))
        d.polygon([(570,610),(680,440),(765,610)], fill=(104,48,40,242))


def _world_ground(d, key: str) -> None:
    fills = {
        "training": (78,139,72,255),
        "country": (128,158,78,255),
        "mountain": (72,92,75,255),
        "night_city": (31,35,43,255),
        "rain": (55,76,67,255),
        "coast": (48,137,164,255),
        "snow": (222,230,232,255),
        "canyon": (143,84,54,255),
        "desert": (194,148,84,255),
        "forest": (42,83,53,255),
        "street": (72,74,78,255),
        "tunnel": (42,44,49,255),
        "neon_rain": (31,34,44,255),
        "alpine": (190,204,202,255),
        "extreme_canyon": (117,64,49,255),
    }
    d.rectangle([0,600,W,H], fill=fills.get(key, (78,139,72,255)))
    # Re-establish signature side geography after the ground plane.
    if key == "coast":
        d.rectangle([0,600,185,1320], fill=(42,142,191,210))
        d.rectangle([W-185,600,W,1320], fill=(35,129,184,205))
    elif key in {"canyon", "extreme_canyon"}:
        extreme = key == "extreme_canyon"
        c1 = (99,46,40,255) if extreme else (151,84,55,255)
        c2 = (83,39,37,255) if extreme else (123,69,47,255)
        inset = 205 if extreme else 150
        d.polygon([(0,600),(inset,600),(145,820),(205,1040),(145,1370),(0,1480)], fill=c1)
        d.polygon([(W,600),(W-inset,600),(W-145,820),(W-205,1040),(W-145,1370),(W,1480)], fill=c2)
    elif key == "tunnel":
        d.rectangle([0,600,155,1580], fill=(24,27,32,255))
        d.rectangle([W-155,600,W,1580], fill=(24,27,32,255))


class _DrawProxy:
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def polygon(self, xy, *args, **kwargs):
        pts = list(xy)
        if _WORLD_STATE["phase"] == "mountain" and pts == _GENERIC_MOUNTAINS:
            _world_horizon(self._inner, _WORLD_STATE["key"])
            _WORLD_STATE["phase"] = "ground"
            return None
        return self._inner.polygon(xy, *args, **kwargs)

    def rectangle(self, xy, *args, **kwargs):
        box = list(xy)
        if _WORLD_STATE["phase"] == "ground" and box == [0,600,W,H]:
            _world_ground(self._inner, _WORLD_STATE["key"])
            _WORLD_STATE["phase"] = "done"
            return None
        return self._inner.rectangle(xy, *args, **kwargs)


def _country_clean(d: ImageDraw.ImageDraw, frame) -> None:
    """Slim countryside fencing with perspective, gaps and occasional trees."""
    posts_by_side: dict[int, list[tuple[float, float, float]]] = {-1: [], 1: []}
    for i, (_, y, s) in enumerate(_base._moving_slots(frame, 8, 0.050)):
        if y < 520 or i in {2, 6}:
            continue
        for side in (-1, 1):
            x = 78 if side < 0 else W - 78
            yy = y + (10 * s if side > 0 and i % 2 else 0)
            posts_by_side[side].append((x, yy, s))

    wood_dark=(86,58,34,238); wood_mid=(113,78,45,230); wood_light=(145,103,60,210)
    for side, posts in posts_by_side.items():
        posts.sort(key=lambda item: item[1])
        for (x0,y0,s0),(x1,y1,s1) in zip(posts, posts[1:]):
            width=max(2,int(2.6*((s0+s1)*0.5)))
            d.line([(x0,y0-31*s0),(x1,y1-31*s1)], fill=wood_mid, width=width)
            d.line([(x0,y0-16*s0),(x1,y1-16*s1)], fill=wood_light, width=max(2,width-1))
        for i,(x,y,s) in enumerate(posts):
            post_w=max(2.0,2.4*s); post_h=47*s
            d.rounded_rectangle([x-post_w,y-post_h,x+post_w,y+3*s], radius=max(1,int(1.8*s)), fill=wood_dark)
            if i % 3 == 1:
                _base._tree(d, x + side*(50+12*s), y+4*s, s*0.60)


# Keep Country rural, not Forest-like, while preserving every other overlay.
_base._country = _country_clean


def render_frame(frame, episode: int, skill: float, frame_no: int):
    key = _road_key(frame)
    _WORLD_STATE["key"] = key
    _WORLD_STATE["phase"] = "mountain"

    # The old Country workaround used the Forest palette. Render Country as Country now.
    original_theme = getattr(frame, "track_theme", key)
    frame.track_theme = key

    globals_dict = _base._base_render_frame.__globals__
    image_draw_module = globals_dict["ImageDraw"]
    original_draw = image_draw_module.Draw

    def draw_factory(*args, **kwargs):
        return _DrawProxy(original_draw(*args, **kwargs))

    image_draw_module.Draw = draw_factory
    try:
        image = _base._base_render_frame(frame, episode=episode, skill=skill, frame_no=frame_no)
    finally:
        image_draw_module.Draw = original_draw
        frame.track_theme = original_theme
        _WORLD_STATE["phase"] = "done"

    # Add each world's moving roadside objects after the base race scene is intact.
    return _base._decorate(image, frame, frame_no)
