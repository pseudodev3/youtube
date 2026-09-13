from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
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


RIVAL_PALETTES = [
    ((44,117,226,255),(91,164,255,255),(18,51,111,255),(148,213,255,255)),
    ((36,184,106,255),(92,224,151,255),(15,92,55,255),(184,255,211,255)),
    ((245,158,40,255),(255,199,92,255),(137,78,15,255),(255,232,160,255)),
    ((155,89,230,255),(199,150,255,255),(78,38,130,255),(229,205,255,255)),
    ((235,235,240,255),(255,255,255,255),(105,108,118,255),(111,211,255,255)),
]


def _car(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float, heading: float,
         player: bool = False, color_id: int = 0):
    sw = 132 * scale
    sh = 218 * scale
    dx = max(-0.08, min(0.08, heading)) * 18 * scale

    if player:
        body = (236,54,50,255); body_light = (255,96,78,255)
        body_dark = (124,25,29,255); accent = (255,211,86,255)
        cockpit = (18,24,32,255)
    else:
        body, body_light, body_dark, accent = RIVAL_PALETTES[color_id % len(RIVAL_PALETTES)]
        cockpit = (13,25,46,255)

    wheel = (18,20,24,255)
    carbon = (28,29,33,255)
    draw.ellipse([cx-sw*.50, cy-sh*.10, cx+sw*.50, cy+sh*.49], fill=(0,0,0,58))

    fw, fh = sw*.15, sh*.16
    rw, rh = sw*.18, sh*.19
    for side in (-1,1):
        sx = cx + side*sw*.43
        draw.rounded_rectangle([sx-fw/2,cy-sh*.24,sx+fw/2,cy-sh*.24+fh], radius=max(2,int(7*scale)), fill=wheel)
        draw.rounded_rectangle([sx-rw/2,cy+sh*.14,sx+rw/2,cy+sh*.14+rh], radius=max(2,int(8*scale)), fill=wheel)

    wing_y = cy-sh*.42
    draw.rounded_rectangle([cx-sw*.43+dx*.18,wing_y,cx+sw*.43+dx*.18,wing_y+sh*.055], radius=max(2,int(7*scale)), fill=carbon)
    draw.rectangle([cx-sw*.47+dx*.18,wing_y+sh*.01,cx-sw*.39+dx*.18,wing_y+sh*.075], fill=body_dark)
    draw.rectangle([cx+sw*.39+dx*.18,wing_y+sh*.01,cx+sw*.47+dx*.18,wing_y+sh*.075], fill=body_dark)

    shell = [
        (cx+dx,cy-sh*.48),(cx+sw*.095+dx*.70,cy-sh*.32),(cx+sw*.17+dx*.42,cy-sh*.13),
        (cx+sw*.31+dx*.20,cy+sh*.02),(cx+sw*.27,cy+sh*.28),(cx+sw*.18,cy+sh*.43),
        (cx-sw*.18,cy+sh*.43),(cx-sw*.27,cy+sh*.28),(cx-sw*.31+dx*.20,cy+sh*.02),
        (cx-sw*.17+dx*.42,cy-sh*.13),(cx-sw*.095+dx*.70,cy-sh*.32),
    ]
    draw.polygon(shell, fill=body)
    draw.polygon([(cx-sw*.27,cy-sh*.04),(cx-sw*.16,cy-sh*.12),(cx-sw*.10,cy+sh*.26),(cx-sw*.21,cy+sh*.34)], fill=body_light)
    draw.polygon([(cx+sw*.27,cy-sh*.04),(cx+sw*.16,cy-sh*.12),(cx+sw*.10,cy+sh*.26),(cx+sw*.21,cy+sh*.34)], fill=body_dark)
    draw.polygon([(cx+dx*.90,cy-sh*.44),(cx+sw*.037,cy-sh*.19),(cx+sw*.045,cy+sh*.20),(cx-sw*.045,cy+sh*.20),(cx-sw*.037,cy-sh*.19)], fill=accent)

    draw.ellipse([cx-sw*.13,cy-sh*.08,cx+sw*.13,cy+sh*.19], fill=cockpit)
    draw.ellipse([cx-sw*.08,cy-sh*.035,cx+sw*.02,cy+sh*.085], fill=(80,96,111,210))
    draw.arc([cx-sw*.12,cy-sh*.055,cx+sw*.12,cy+sh*.075], start=190,end=350, fill=(42,44,48,255), width=max(2,int(7*scale)))

    draw.polygon([(cx-sw*.16,cy+sh*.18),(cx+sw*.16,cy+sh*.18),(cx+sw*.20,cy+sh*.37),(cx-sw*.20,cy+sh*.37)], fill=body_dark)
    draw.rounded_rectangle([cx-sw*.40,cy+sh*.37,cx+sw*.40,cy+sh*.44], radius=max(2,int(7*scale)), fill=carbon)
    draw.rounded_rectangle([cx-sw*.28,cy+sh*.335,cx+sw*.28,cy+sh*.375], radius=max(2,int(5*scale)), fill=accent)

    if player:
        lamp_y = cy+sh*.285
        draw.rounded_rectangle([cx-sw*.14,lamp_y,cx-sw*.035,lamp_y+sh*.052], radius=max(2,int(4*scale)), fill=(255,219,92,255))
        draw.rounded_rectangle([cx+sw*.035,lamp_y,cx+sw*.14,lamp_y+sh*.052], radius=max(2,int(4*scale)), fill=(255,219,92,255))


def _rotated_car(img: Image.Image, cx: float, cy: float, scale: float, angle_deg: float,
                 player: bool = False, color_id: int = 0):
    """Rotate the whole car sprite, used only for real drifts/spins."""
    box = int(max(300, 360 * scale))
    layer = Image.new("RGBA", (box, box), (0,0,0,0))
    ld = ImageDraw.Draw(layer, "RGBA")
    _car(ld, box/2, box/2, scale, 0.0, player, color_id)
    rotated = layer.rotate(-angle_deg, resample=Image.Resampling.BICUBIC, expand=True)
    x = int(cx - rotated.width/2)
    y = int(cy - rotated.height/2)
    img.paste(rotated, (x,y), rotated)


def _road_center(p: float, frame, cam_x: float) -> float:
    near = frame.road_curve * (p ** 1.62) * 700
    far = frame.road_curve_far * math.sin(p * math.pi) * 300
    sweep = math.sin(frame.t * .14 + p * 3.0) * 50 * p
    return W/2 + near + far + sweep + cam_x


def render_frame(frame, episode: int, skill: float, frame_no: int) -> Image.Image:
    rng = random.Random(frame_no // 3)
    img = Image.new("RGB", (W,H), (116,174,224))
    d = ImageDraw.Draw(img, "RGBA")

    for y in range(0,HORIZON,8):
        p = y/HORIZON
        d.rectangle([0,y,W,y+8], fill=(int(95+50*p),int(155+48*p),int(220+25*p),255))

    mountains = [(0,610),(120,500),(235,585),(360,455),(480,565),(620,430),(760,555),(900,470),(1080,585),(1080,760),(0,760)]
    d.polygon(mountains, fill=(81,111,122,255))
    d.rectangle([0,600,W,H], fill=(78,139,72,255))

    # Keep the camera calm. Action now comes from racing/drifting, not screen shake.
    cam_x = int(frame.player.heading * 18 + (rng.random()-.5) * 7 * frame.shake)
    horizon_y = HORIZON + int(frame.shake * 2)

    width_mul = frame.road_width / 0.82
    slices = 110
    for j in range(slices):
        p0 = j/slices; p1 = (j+1)/slices
        y0 = horizon_y + (p0**1.72)*(H-horizon_y)
        y1 = horizon_y + (p1**1.72)*(H-horizon_y)
        half0 = (65 + (p0**1.28)*ROAD_BOTTOM) * width_mul
        half1 = (65 + (p1**1.28)*ROAD_BOTTOM) * width_mul
        c0 = _road_center(p0, frame, cam_x)
        c1 = _road_center(p1, frame, cam_x)

        grass = (72,132,67,255) if j%2 else (76,143,70,255)
        d.polygon([(0,y0),(W,y0),(W,y1),(0,y1)], fill=grass)
        shoulder = 28+p1*30
        d.polygon([(c0-half0-shoulder,y0),(c0+half0+shoulder,y0),(c1+half1+shoulder,y1),(c1-half1-shoulder,y1)], fill=(204,204,196,255))
        road = (50,52,55,255) if j%2 else (54,56,59,255)
        d.polygon([(c0-half0,y0),(c0+half0,y0),(c1+half1,y1),(c1-half1,y1)], fill=road)

        curb = (237,62,55,255) if (j//3)%2 else (242,242,235,255)
        cw0,cw1=max(2,half0*.045),max(2,half1*.045)
        d.polygon([(c0-half0,y0),(c0-half0+cw0,y0),(c1-half1+cw1,y1),(c1-half1,y1)], fill=curb)
        d.polygon([(c0+half0-cw0,y0),(c0+half0,y0),(c1+half1,y1),(c1+half1-cw1,y1)], fill=curb)

        if (j-int(frame.t*(34+frame.player.speed*28)))%11 < 5 and j>8:
            lw0=max(2,half0*.016); lw1=max(2,half1*.016)
            d.polygon([(c0-lw0,y0),(c0+lw0,y0),(c1+lw1,y1),(c1-lw1,y1)], fill=(245,240,210,225))

    # Chevron boards appear on the outside of harder bends so the road reads as a
    # genuine corner/hairpin instead of a moving straight strip.
    if abs(frame.road_curve) > .45:
        outside = 1 if frame.road_curve > 0 else -1
        for n in range(4):
            p = .48 + n*.09
            y = horizon_y + (p**1.72)*(H-horizon_y)
            half = (65+(p**1.28)*ROAD_BOTTOM) * width_mul
            center = _road_center(p,frame,cam_x)
            x = center + outside*(half+62)
            s = 12 + 24*p
            d.rectangle([x-s,y-s*.55,x+s,y+s*.55], fill=(245,210,45,245))
            direction = -outside
            pts=[(x-direction*s*.45,y-s*.32),(x+direction*s*.35,y),(x-direction*s*.45,y+s*.32)]
            d.line(pts, fill=(24,27,31,255), width=max(3,int(s*.18)), joint="curve")

    for k in range(14):
        p=((k/14)+(frame.t*(.13+frame.player.speed*.10)))%1.0
        y=horizon_y+(p**1.72)*(H-horizon_y)
        half=(65+(p**1.28)*ROAD_BOTTOM) * width_mul
        center=_road_center(p,frame,cam_x)
        size=8+28*p
        for side in (-1,1):
            x=center+side*(half+55+50*p)
            d.rectangle([x-size*.18,y-size*1.8,x+size*.18,y], fill=(245,245,238,255))
            d.rectangle([x-size*.18,y-size*1.15,x+size*.18,y-size*.78], fill=(28,28,30,255))

    # Fixed field only: once a rival has left the race view it stays gone.
    for rival in sorted([r for r in frame.rivals if r.active], key=lambda r:r.z):
        if rival.z < 0.0 or rival.z > 1.18:
            continue
        p=.10+rival.z*.72
        y=horizon_y+(p**1.72)*(H-horizon_y)
        half=(65+(p**1.28)*ROAD_BOTTOM) * width_mul
        center=_road_center(p,frame,cam_x)
        x=center+rival.lane*half*.68
        scale=.62+.52*p

        if rival.behavior == "spin" or abs(rival.rotation) > .10:
            angle = rival.rotation * 70.0
            _rotated_car(img,x,y,scale,angle,False,rival.color)
            d = ImageDraw.Draw(img,"RGBA")
            # comic smoke puff makes the spin obvious
            for n in range(5):
                rr = rng.uniform(6,15)*scale
                sx=x+rng.uniform(-28,28)*scale
                sy=y+rng.uniform(30,85)*scale
                d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,rng.randint(35,80)))
        else:
            _car(d,x,y,scale,rival.heading,False,rival.color)

        # Panic braking is visible, not just a text event.
        if rival.behavior == "panic":
            s=scale
            d.ellipse([x-38*s,y+62*s,x-22*s,y+78*s],fill=(255,65,45,220))
            d.ellipse([x+22*s,y+62*s,x+38*s,y+78*s],fill=(255,65,45,220))

    py=1605
    pp=((py-horizon_y)/(H-horizon_y))**(1/1.72)
    phalf=(65+(pp**1.28)*ROAD_BOTTOM) * width_mul
    pcenter=_road_center(pp,frame,cam_x)
    px=pcenter+frame.player.lane*phalf*.68

    # Bigger smoke, longer skid arcs, and whole-car rotation make drift unmistakable.
    if frame.player.drifting:
        drift_dir = 1 if frame.player.drift_angle > 0 else -1
        for n in range(20):
            sy=py+72+rng.uniform(0,190)
            sx=px+rng.uniform(-72,72)-drift_dir*(sy-py)*.24
            r=rng.uniform(12,32)
            d.ellipse([sx-r,sy-r,sx+r,sy+r], fill=(220,224,228,rng.randint(35,85)))
        for side in (-1,1):
            sx=px+side*54
            d.line([(sx,py+78),(sx-drift_dir*105,py+285)], fill=(18,18,20,115), width=10)
    elif abs(frame.player.heading)>.15 or frame.player.crashed:
        for side in (-1,1):
            sx=px+side*54
            d.line([(sx,py+76),(sx-frame.player.heading*100,py+190)], fill=(14,14,16,70), width=7)

    if frame.player.crashed:
        for n in range(16):
            ang=rng.uniform(math.pi*.05,math.pi*.95); dist=rng.uniform(24,130)
            sx=px+math.cos(ang)*dist; sy=py+math.sin(ang)*dist; r=rng.uniform(3,8)
            d.ellipse([sx-r,sy-r,sx+r,sy+r], fill=rng.choice([(255,210,80,220),(255,118,48,220),(255,240,170,210)]))

    if frame.player.drifting and abs(frame.player.drift_angle) > .08:
        _rotated_car(img,px,py,1.15,frame.player.drift_angle*42.0,True,0)
        d=ImageDraw.Draw(img,"RGBA")
    else:
        _car(d,px,py,1.15,frame.player.heading,True,0)

    d.rounded_rectangle([48,52,W-48,240], radius=34, fill=(9,14,21,182), outline=(255,255,255,45), width=2)
    f1=_font(54,True); f2=_font(34,True)
    d.text((82,78),f"EP. {episode:03d}",font=f1,fill=(255,255,255,255))
    level=max(1,int(skill*100))
    d.text((82,151),f"DRIVER LEVEL {level}",font=f2,fill=(237,242,248,255))
    d.text((W-330,95),f"{int(frame.player.speed*310):03d} KM/H",font=f2,fill=(255,224,126,255))

    bx0,by0,bx1,by1=82,211,W-82,226
    d.rounded_rectangle([bx0,by0,bx1,by1],radius=7,fill=(255,255,255,42))
    d.rounded_rectangle([bx0,by0,bx0+(bx1-bx0)*skill,by1],radius=7,fill=(255,213,90,245))

    if frame.event_text:
        text=frame.event_text
        box=d.textbbox((0,0),text,font=f1); tw=box[2]-box[0]
        d.rounded_rectangle([W/2-tw/2-34,330,W/2+tw/2+34,420],radius=24,fill=(0,0,0,178),outline=(255,255,255,34),width=2)
        d.text((W/2-tw/2,346),text,font=f1,fill=(255,255,255,255))

    label="BEGINNER" if skill<.28 else "GETTING GOOD" if skill<.58 else "PRO"
    d.rounded_rectangle([60,1740,W-60,1850],radius=30,fill=(8,10,14,205))
    bbox=d.textbbox((0,0),label,font=f1); tw=bbox[2]-bbox[0]
    d.text((W/2-tw/2,1766),label,font=f1,fill=(255,255,255,255))

    if frame.shake>.2:
        overlay=Image.new("RGBA",(W,H),(255,255,255,int(20*min(1.0,frame.shake))))
        img=Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")
    return img
