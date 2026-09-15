from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

from renderer import W, H, render_frame as _base_render_frame


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


def _moving_slots(frame, count: int, speed: float = 0.08):
    for i in range(count):
        p = ((i / count) + frame.t * speed) % 1.0
        y = 470 + (p ** 1.55) * 1040
        scale = 0.28 + p * 1.15
        yield p, y, scale


def _tree(d: ImageDraw.ImageDraw, x: float, y: float, s: float, dark: bool = False) -> None:
    trunk = (74, 52, 34, 235) if not dark else (41, 35, 30, 245)
    leaf1 = (54, 118, 59, 242) if not dark else (28, 72, 45, 248)
    leaf2 = (76, 145, 67, 228) if not dark else (38, 92, 53, 235)
    d.rectangle([x - 7*s, y - 74*s, x + 7*s, y], fill=trunk)
    d.ellipse([x - 40*s, y - 124*s, x + 40*s, y - 50*s], fill=leaf1)
    d.ellipse([x - 30*s, y - 151*s, x + 32*s, y - 82*s], fill=leaf2)


def _pine(d: ImageDraw.ImageDraw, x: float, y: float, s: float, snowy: bool = False) -> None:
    trunk = (67, 50, 38, 240)
    green = (35, 87, 55, 245)
    snow = (235, 243, 247, 225)
    d.rectangle([x - 5*s, y - 72*s, x + 5*s, y], fill=trunk)
    for n, width in enumerate((45, 36, 28)):
        cy = y - (52 + n*28) * s
        d.polygon([(x, cy - 45*s), (x - width*s, cy + 18*s), (x + width*s, cy + 18*s)], fill=green)
        if snowy:
            d.line([(x - width*.72*s, cy + 6*s), (x + width*.72*s, cy + 6*s)], fill=snow, width=max(2, int(5*s)))


def _country(d: ImageDraw.ImageDraw, frame) -> None:
    for i, (_, y, s) in enumerate(_moving_slots(frame, 10, 0.055)):
        for side in (-1, 1):
            x = 92 if side < 0 else W - 92
            post = (111, 78, 45, 245)
            d.rectangle([x - 5*s, y - 45*s, x + 5*s, y + 5*s], fill=post)
            d.line([(x - 58*s, y - 30*s), (x + 58*s, y - 30*s)], fill=(137, 97, 56, 220), width=max(2, int(5*s)))
            d.line([(x - 58*s, y - 12*s), (x + 58*s, y - 12*s)], fill=(137, 97, 56, 205), width=max(2, int(4*s)))
            if i % 3 == 0:
                _tree(d, x + side * 62*s, y + 2*s, s * 0.72)


def _mountain(d: ImageDraw.ImageDraw, frame, alpine: bool = False) -> None:
    peak = (98, 111, 119, 225) if not alpine else (210, 224, 232, 235)
    dark = (64, 77, 83, 235) if not alpine else (121, 145, 157, 225)
    d.polygon([(0, 640), (90, 410), (165, 585), (245, 330), (330, 640)], fill=dark)
    d.polygon([(W, 640), (W-105, 390), (W-185, 570), (W-275, 315), (W-350, 640)], fill=peak)
    if alpine:
        for x in (48, 155, W-155, W-48):
            _pine(d, x, 950, 0.9, snowy=True)
    else:
        for _, y, s in _moving_slots(frame, 8, 0.07):
            for x in (76, W-76):
                d.rectangle([x-42*s, y-8*s, x+42*s, y+5*s], fill=(161, 165, 161, 230))
                d.rectangle([x-38*s, y-2*s, x+38*s, y+3*s], fill=(222, 225, 219, 190))


def _city(d: ImageDraw.ImageDraw, frame, neon: bool = False) -> None:
    rng = random.Random(4400 + int(frame.t * 2))
    for side in (-1, 1):
        base_x = 0 if side < 0 else W - 185
        for i in range(3):
            w = 52 + i*18
            h = 220 + i*95
            x0 = base_x + i*42 if side < 0 else base_x + 90 - i*36
            y0 = 650 - h
            body = (18, 24, 35, 238) if neon else (35, 41, 50, 235)
            d.rectangle([x0, y0, x0+w, 650], fill=body)
            for wy in range(int(y0+22), 625, 32):
                glow = (77, 229, 255, 220) if neon and (wy//32)%2 else (255, 209, 91, 175)
                for wx in range(int(x0+10), int(x0+w-6), 20):
                    if rng.random() > 0.28:
                        d.rectangle([wx, wy, wx+7, wy+10], fill=glow)
    if neon:
        for y in (760, 1010, 1260):
            d.rectangle([25, y, 118, y+12], fill=(255, 55, 211, 205))
            d.rectangle([W-118, y+18, W-25, y+30], fill=(47, 228, 255, 215))


def _coast(d: ImageDraw.ImageDraw, frame) -> None:
    d.rectangle([0, 575, 185, 1310], fill=(42, 142, 191, 150))
    d.rectangle([W-185, 575, W, 1310], fill=(35, 129, 184, 140))
    d.ellipse([W-175, 245, W-95, 325], fill=(255, 218, 112, 225))
    for _, y, s in _moving_slots(frame, 8, 0.06):
        for x in (135, W-135):
            d.rectangle([x-50*s, y-6*s, x+50*s, y+5*s], fill=(211, 213, 205, 230))
            d.rectangle([x-43*s, y-2*s, x+43*s, y+2*s], fill=(91, 98, 102, 180))


def _snow(d: ImageDraw.ImageDraw, frame) -> None:
    rng = random.Random(8200 + int(frame.t * 12))
    for x0, x1 in ((0, 155), (W-155, W)):
        d.rectangle([x0, 660, x1, 1510], fill=(229, 239, 243, 120))
    for _ in range(42):
        x = rng.randrange(0, W)
        y = rng.randrange(220, 1540)
        r = rng.randrange(2, 6)
        d.ellipse([x-r, y-r, x+r, y+r], fill=(250, 252, 255, 155))
    for x in (58, 132, W-132, W-58):
        _pine(d, x, 1050, 0.72, snowy=True)


def _canyon(d: ImageDraw.ImageDraw, extreme: bool = False) -> None:
    rock1 = (126, 67, 48, 240) if extreme else (157, 91, 59, 230)
    rock2 = (92, 46, 39, 245) if extreme else (126, 72, 48, 235)
    left = [(0, 370), (125, 430), (88, 650), (165, 820), (105, 1010), (180, 1210), (130, 1510), (0, 1600)]
    right = [(W, 350), (W-125, 425), (W-82, 645), (W-170, 805), (W-110, 1015), (W-188, 1195), (W-138, 1510), (W, 1600)]
    d.polygon(left, fill=rock1)
    d.polygon(right, fill=rock2)
    if extreme:
        for y in (710, 900, 1090, 1280):
            d.polygon([(20,y),(82,y-22),(82,y+22)], fill=(255,211,62,230))
            d.polygon([(W-20,y),(W-82,y-22),(W-82,y+22)], fill=(255,211,62,230))


def _desert(d: ImageDraw.ImageDraw, frame) -> None:
    d.polygon([(0,690),(150,620),(260,690),(180,790),(0,830)], fill=(216, 171, 102, 190))
    d.polygon([(W,680),(W-150,610),(W-275,705),(W-175,800),(W,825)], fill=(227, 183, 112, 185))
    for i, (_, y, s) in enumerate(_moving_slots(frame, 7, 0.05)):
        if i % 2:
            continue
        for x in (76, W-76):
            green = (61, 108, 68, 230)
            d.rectangle([x-6*s, y-80*s, x+6*s, y], fill=green)
            d.rectangle([x-25*s, y-56*s, x+6*s, y-46*s], fill=green)
            d.rectangle([x-25*s, y-72*s, x-17*s, y-46*s], fill=green)


def _forest(d: ImageDraw.ImageDraw, frame) -> None:
    d.rectangle([0, 240, 145, 1510], fill=(21, 58, 38, 85))
    d.rectangle([W-145, 240, W, 1510], fill=(21, 58, 38, 85))
    for i, (_, y, s) in enumerate(_moving_slots(frame, 12, 0.07)):
        if i % 2 == 0:
            _tree(d, 58, y, s*0.82, dark=True)
            _tree(d, W-58, y, s*0.82, dark=True)


def _street(d: ImageDraw.ImageDraw, frame) -> None:
    for side in (-1, 1):
        x0, x1 = (0, 138) if side < 0 else (W-138, W)
        d.rectangle([x0, 560, x1, 1510], fill=(93, 96, 101, 185))
        for y in range(620, 1450, 120):
            d.rectangle([x0+12, y, x1-12, y+16], fill=(225, 225, 218, 165))
    for x in (48, W-48):
        for y in (690, 930, 1170):
            d.rectangle([x-28, y-82, x+28, y], fill=(29, 34, 41, 230))
            d.rectangle([x-18, y-68, x+18, y-48], fill=(244, 202, 76, 185))


def _tunnel(d: ImageDraw.ImageDraw) -> None:
    wall = (18, 21, 27, 178)
    d.rectangle([0, 210, 150, 1580], fill=wall)
    d.rectangle([W-150, 210, W, 1580], fill=wall)
    d.rectangle([0, 210, W, 285], fill=(14, 17, 22, 155))
    for y in range(330, 1450, 150):
        d.rectangle([34, y, 112, y+11], fill=(245, 224, 166, 210))
        d.rectangle([W-112, y, W-34, y+11], fill=(245, 224, 166, 210))


def _rain(d: ImageDraw.ImageDraw, frame, neon: bool = False) -> None:
    rng = random.Random(17000 + int(frame.t*30))
    color = (100, 221, 255, 120) if neon else (213, 230, 243, 82)
    for _ in range(42):
        x = rng.randrange(0, W)
        y = rng.randrange(200, 1550)
        d.line([(x, y), (x-8, y+34)], fill=color, width=2)


def _decorate(img: Image.Image, frame, frame_no: int) -> Image.Image:
    key = _road_key(frame)
    if key == "training":
        return img

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # Gentle map tint below the HUD makes unlocks obvious without recoloring cars.
    tint = {
        "country": (238, 202, 119, 12),
        "mountain": (130, 158, 178, 14),
        "night_city": (42, 67, 115, 20),
        "rain": (83, 111, 139, 16),
        "coast": (54, 174, 211, 13),
        "snow": (225, 240, 246, 15),
        "canyon": (215, 119, 69, 14),
        "desert": (231, 178, 93, 14),
        "forest": (33, 95, 53, 15),
        "street": (119, 124, 132, 12),
        "tunnel": (17, 22, 31, 34),
        "neon_rain": (95, 44, 140, 20),
        "alpine": (200, 226, 237, 14),
        "extreme_canyon": (159, 62, 45, 18),
    }.get(key)
    if tint:
        d.rectangle([0, 190, W, H], fill=tint)

    if key == "country":
        _country(d, frame)
    elif key == "mountain":
        _mountain(d, frame)
    elif key == "night_city":
        _city(d, frame)
    elif key == "rain":
        _rain(d, frame)
    elif key == "coast":
        _coast(d, frame)
    elif key == "snow":
        _snow(d, frame)
    elif key == "canyon":
        _canyon(d, extreme=False)
    elif key == "desert":
        _desert(d, frame)
    elif key == "forest":
        _forest(d, frame)
    elif key == "street":
        _street(d, frame)
    elif key == "tunnel":
        _tunnel(d)
    elif key == "neon_rain":
        _city(d, frame, neon=True)
        _rain(d, frame, neon=True)
    elif key == "alpine":
        _mountain(d, frame, alpine=True)
        _snow(d, frame)
    elif key == "extreme_canyon":
        _canyon(d, extreme=True)

    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def render_frame(frame, episode: int, skill: float, frame_no: int) -> Image.Image:
    base = _base_render_frame(frame, episode=episode, skill=skill, frame_no=frame_no)
    return _decorate(base, frame, frame_no)
