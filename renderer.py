from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os
import random

W, H = 1080, 1920
HORIZON = 560
ROAD_BOTTOM = 980


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _car(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float, heading: float, player: bool = False):
    """Polished arcade Formula-style car rendered procedurally."""
    sw = 132 * scale
    sh = 218 * scale
    dx = max(-0.30, min(0.30, heading)) * 115 * scale

    if player:
        body = (236, 54, 50, 255)
        body_light = (255, 96, 78, 255)
        body_dark = (124, 25, 29, 255)
        accent = (255, 211, 86, 255)
        cockpit = (18, 24, 32, 255)
    else:
        body = (44, 117, 226, 255)
        body_light = (91, 164, 255, 255)
        body_dark = (18, 51, 111, 255)
        accent = (148, 213, 255, 255)
        cockpit = (13, 25, 46, 255)

    wheel = (18, 20, 24, 255)
    carbon = (28, 29, 33, 255)

    # Ground shadow: narrower and lower so the car feels planted instead of floating.
    draw.ellipse(
        [cx - sw * .50, cy - sh * .10, cx + sw * .50, cy + sh * .49],
        fill=(0, 0, 0, 62),
    )

    # Exposed tyres - front pair smaller, rear pair chunkier.
    fw, fh = sw * .15, sh * .16
    rw, rh = sw * .18, sh * .19
    for side in (-1, 1):
        sx = cx + side * sw * .43
        draw.rounded_rectangle(
            [sx-fw/2, cy-sh*.24, sx+fw/2, cy-sh*.24+fh],
            radius=max(2, int(7*scale)), fill=wheel,
        )
        draw.rounded_rectangle(
            [sx-rw/2, cy+sh*.14, sx+rw/2, cy+sh*.14+rh],
            radius=max(2, int(8*scale)), fill=wheel,
        )

    # Front wing.
    wing_y = cy - sh * .42
    draw.rounded_rectangle(
        [cx-sw*.43+dx*.18, wing_y, cx+sw*.43+dx*.18, wing_y+sh*.055],
        radius=max(2, int(7*scale)), fill=carbon,
    )
    draw.rectangle(
        [cx-sw*.47+dx*.18, wing_y+sh*.01, cx-sw*.39+dx*.18, wing_y+sh*.075],
        fill=body_dark,
    )
    draw.rectangle(
        [cx+sw*.39+dx*.18, wing_y+sh*.01, cx+sw*.47+dx*.18, wing_y+sh*.075],
        fill=body_dark,
    )

    # Main open-wheel body: narrow nose, broad sidepods, tapered rear.
    shell = [
        (cx + dx, cy - sh*.48),
        (cx + sw*.095 + dx*.70, cy - sh*.32),
        (cx + sw*.17 + dx*.42, cy - sh*.13),
        (cx + sw*.31 + dx*.20, cy + sh*.02),
        (cx + sw*.27, cy + sh*.28),
        (cx + sw*.18, cy + sh*.43),
        (cx - sw*.18, cy + sh*.43),
        (cx - sw*.27, cy + sh*.28),
        (cx - sw*.31 + dx*.20, cy + sh*.02),
        (cx - sw*.17 + dx*.42, cy - sh*.13),
        (cx - sw*.095 + dx*.70, cy - sh*.32),
    ]
    draw.polygon(shell, fill=body)

    # Left/right body shading adds volume.
    draw.polygon([
        (cx-sw*.27+dx*.18, cy-sh*.04),
        (cx-sw*.16+dx*.34, cy-sh*.12),
        (cx-sw*.10, cy+sh*.26),
        (cx-sw*.21, cy+sh*.34),
    ], fill=body_light)
    draw.polygon([
        (cx+sw*.27+dx*.18, cy-sh*.04),
        (cx+sw*.16+dx*.34, cy-sh*.12),
        (cx+sw*.10, cy+sh*.26),
        (cx+sw*.21, cy+sh*.34),
    ], fill=body_dark)

    # Long nose highlight / livery stripe.
    draw.polygon([
        (cx+dx*.90, cy-sh*.44),
        (cx+sw*.037+dx*.55, cy-sh*.19),
        (cx+sw*.045, cy+sh*.20),
        (cx-sw*.045, cy+sh*.20),
        (cx-sw*.037+dx*.55, cy-sh*.19),
    ], fill=accent)

    # Cockpit / halo area.
    draw.ellipse(
        [cx-sw*.13+dx*.20, cy-sh*.08, cx+sw*.13+dx*.20, cy+sh*.19],
        fill=cockpit,
    )
    draw.ellipse(
        [cx-sw*.08+dx*.18, cy-sh*.035, cx+sw*.02+dx*.18, cy+sh*.085],
        fill=(80, 96, 111, 210),
    )
    halo_y = cy + sh*.005
    draw.arc(
        [cx-sw*.12+dx*.20, halo_y-sh*.06, cx+sw*.12+dx*.20, halo_y+sh*.07],
        start=190, end=350, fill=(42, 44, 48, 255), width=max(2, int(7*scale)),
    )

    # Rear engine cover and wing assembly.
    draw.polygon([
        (cx-sw*.16, cy+sh*.18),
        (cx+sw*.16, cy+sh*.18),
        (cx+sw*.20, cy+sh*.37),
        (cx-sw*.20, cy+sh*.37),
    ], fill=body_dark)
    draw.rounded_rectangle(
        [cx-sw*.40, cy+sh*.37, cx+sw*.40, cy+sh*.44],
        radius=max(2, int(7*scale)), fill=carbon,
    )
    draw.rounded_rectangle(
        [cx-sw*.28, cy+sh*.335, cx+sw*.28, cy+sh*.375],
        radius=max(2, int(5*scale)), fill=accent,
    )

    # Small rear lamps / hot exhaust detail for the hero car.
    if player:
        lamp_y = cy + sh*.285
        draw.rounded_rectangle(
            [cx-sw*.14, lamp_y, cx-sw*.035, lamp_y+sh*.052],
            radius=max(2, int(4*scale)), fill=(255, 219, 92, 255),
        )
        draw.rounded_rectangle(
            [cx+sw*.035, lamp_y, cx+sw*.14, lamp_y+sh*.052],
            radius=max(2, int(4*scale)), fill=(255, 219, 92, 255),
        )


def render_frame(frame, episode: int, skill: float, frame_no: int) -> Image.Image:
    rng = random.Random(frame_no // 3)
    img = Image.new("RGB", (W, H), (116, 174, 224))
    d = ImageDraw.Draw(img, "RGBA")

    # sky gradient bands
    for y in range(0, HORIZON, 8):
        p = y / HORIZON
        d.rectangle([0,y,W,y+8], fill=(int(95+50*p), int(155+48*p), int(220+25*p), 255))

    # distant mountains and treeline
    mountains = [(0,610),(120,500),(235,585),(360,455),(480,565),(620,430),(760,555),(900,470),(1080,585),(1080,760),(0,760)]
    d.polygon(mountains, fill=(81,111,122,255))
    d.rectangle([0,600,W,H], fill=(78,139,72,255))

    shake_x = int((rng.random()-.5) * 18 * frame.shake)
    curve = frame.road_curve

    # road slices: perspective widening + curve accumulation
    slices = 105
    centers = []
    for j in range(slices):
        p0 = j / slices
        p1 = (j+1) / slices
        y0 = HORIZON + (p0**1.72) * (H-HORIZON)
        y1 = HORIZON + (p1**1.72) * (H-HORIZON)
        half0 = 65 + (p0**1.28) * ROAD_BOTTOM
        half1 = 65 + (p1**1.28) * ROAD_BOTTOM
        bend0 = curve * (p0**2.05) * 420 + math.sin(frame.t*.33) * p0 * 75
        bend1 = curve * (p1**2.05) * 420 + math.sin(frame.t*.33) * p1 * 75
        c0 = W/2 + bend0 + shake_x
        c1 = W/2 + bend1 + shake_x
        centers.append((y1,c1,half1))

        grass = (72,132,67,255) if j % 2 else (76,143,70,255)
        d.polygon([(0,y0),(W,y0),(W,y1),(0,y1)], fill=grass)
        shoulder = 28 + p1*30
        d.polygon([(c0-half0-shoulder,y0),(c0+half0+shoulder,y0),(c1+half1+shoulder,y1),(c1-half1-shoulder,y1)], fill=(204,204,196,255))
        road = (50,52,55,255) if j % 2 else (54,56,59,255)
        d.polygon([(c0-half0,y0),(c0+half0,y0),(c1+half1,y1),(c1-half1,y1)], fill=road)

        # curbs
        curb = (237,62,55,255) if (j//3)%2 else (242,242,235,255)
        curbw0, curbw1 = max(2, half0*.045), max(2, half1*.045)
        d.polygon([(c0-half0,y0),(c0-half0+curbw0,y0),(c1-half1+curbw1,y1),(c1-half1,y1)], fill=curb)
        d.polygon([(c0+half0-curbw0,y0),(c0+half0,y0),(c1+half1,y1),(c1+half1-curbw1,y1)], fill=curb)

        # dashed center line
        if (j + int(frame.t*22)) % 12 < 6 and j > 10:
            lw0 = max(2, half0*.016); lw1=max(2,half1*.016)
            d.polygon([(c0-lw0,y0),(c0+lw0,y0),(c1+lw1,y1),(c1-lw1,y1)], fill=(245,240,210,210))

    # roadside posts
    for k in range(12):
        p = ((k/12)+(frame.t*.10)) % 1.0
        y = HORIZON + (p**1.72)*(H-HORIZON)
        half = 65 + (p**1.28)*ROAD_BOTTOM
        center = W/2 + curve*(p**2.05)*420 + math.sin(frame.t*.33)*p*75 + shake_x
        size = 8 + 28*p
        for side in (-1,1):
            x = center + side*(half+55+50*p)
            d.rectangle([x-size*.18,y-size*1.8,x+size*.18,y], fill=(245,245,238,255))
            d.rectangle([x-size*.18,y-size*1.15,x+size*.18,y-size*.78], fill=(28,28,30,255))

    # rivals from far to near
    for z,lane,_pace in sorted(frame.rivals, key=lambda r:r[0]):
        p = 0.16 + z*0.63
        y = HORIZON + (p**1.72)*(H-HORIZON)
        half = 65 + (p**1.28)*ROAD_BOTTOM
        center = W/2 + curve*(p**2.05)*420 + math.sin(frame.t*.33)*p*75 + shake_x
        x = center + lane*half*.68
        _car(d,x,y,0.16+0.46*p,0.0,False)

    # player car
    py = 1605
    pp = ((py-HORIZON)/(H-HORIZON))**(1/1.72)
    phalf = 65 + (pp**1.28)*ROAD_BOTTOM
    pcenter = W/2 + curve*(pp**2.05)*420 + math.sin(frame.t*.33)*pp*75 + shake_x
    px = pcenter + frame.player.lane*phalf*.68
    _car(d,px,py,1.15,frame.player.heading,True)

    # top glass HUD
    d.rounded_rectangle([48,52,W-48,240], radius=34, fill=(9,14,21,182), outline=(255,255,255,45), width=2)
    f1 = _font(54,True); f2=_font(34,True); f3=_font(30,False)
    d.text((82,78), f"EP. {episode:03d}", font=f1, fill=(255,255,255,255))
    level = max(1,int(skill*100))
    d.text((82,151), f"DRIVER LEVEL {level}", font=f2, fill=(237,242,248,255))
    d.text((W-330,95), f"{int(frame.player.speed*310):03d} KM/H", font=f2, fill=(255,224,126,255))

    # progress bar
    bx0,by0,bx1,by1=82,211,W-82,226
    d.rounded_rectangle([bx0,by0,bx1,by1], radius=7, fill=(255,255,255,42))
    d.rounded_rectangle([bx0,by0,bx0+(bx1-bx0)*skill,by1], radius=7, fill=(255,213,90,245))

    # center event card
    if frame.event_text:
        text=frame.event_text
        box=d.textbbox((0,0),text,font=f1)
        tw=box[2]-box[0]
        d.rounded_rectangle([W/2-tw/2-34,330,W/2+tw/2+34,420],radius=24,fill=(0,0,0,170))
        d.text((W/2-tw/2,346),text,font=f1,fill=(255,255,255,255))

    # lower caption anchors the format
    label = "BEGINNER" if skill < .28 else "GETTING GOOD" if skill < .58 else "PRO"
    d.rounded_rectangle([60,1740,W-60,1850],radius=30,fill=(8,10,14,205))
    bbox=d.textbbox((0,0),label,font=f1); tw=bbox[2]-bbox[0]
    d.text((W/2-tw/2,1766),label,font=f1,fill=(255,255,255,255))

    if frame.shake > .2:
        # subtle impact bloom
        overlay=Image.new("RGBA",(W,H),(255,255,255,int(35*frame.shake)))
        img=Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")
    return img
