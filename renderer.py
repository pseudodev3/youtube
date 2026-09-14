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


def _rotate_point(x: float, y: float, angle_deg: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a)


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

    # Fixed recurring cast. When a driver does something stupid, label that car for
    # a moment so viewers learn the personalities across episodes.
    tiny = _font(22, True)
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
            for n in range(7):
                rr = rng.uniform(6,17)*scale
                sx=x+rng.uniform(-32,32)*scale
                sy=y+rng.uniform(30,92)*scale
                d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,rng.randint(35,90)))
        else:
            _car(d,x,y,scale,rival.heading,False,rival.color)

        if rival.behavior in {"panic", "brake_check"}:
            s=scale
            d.ellipse([x-40*s,y+62*s,x-20*s,y+80*s],fill=(255,65,45,240))
            d.ellipse([x+20*s,y+62*s,x+40*s,y+80*s],fill=(255,65,45,240))

        if rival.behavior != "normal" and p > .30:
            text = rival.name
            bb = d.textbbox((0,0), text, font=tiny)
            tw = bb[2]-bb[0]
            ty = y - 125*scale
            d.rounded_rectangle([x-tw/2-10,ty-4,x+tw/2+10,ty+28],radius=8,fill=(0,0,0,150))
            d.text((x-tw/2,ty),text,font=tiny,fill=(255,255,255,230))

    py=1605
    pp=((py-horizon_y)/(H-horizon_y))**(1/1.72)
    phalf=(65+(pp**1.28)*ROAD_BOTTOM) * width_mul
    pcenter=_road_center(pp,frame,cam_x)
    px=pcenter+frame.player.lane*phalf*.68

    # Proper drift read: body points INTO the corner while the car's actual path slides
    # OUTWARD. Rear-tyre smoke originates from rotated rear-wheel locations and trails
    # along the slip direction instead of straight down the screen.
    drift_angle_deg = frame.player.drift_angle * 54.0
    if frame.player.drifting:
        slip_dir = 1 if frame.player.drift_slip > 0 else -1
        rear_points = [(-56, 72), (56, 72)]
        for local_x, local_y in rear_points:
            rx, ry = _rotate_point(local_x, local_y, drift_angle_deg)
            tx, ty = px + rx, py + ry
            for n in range(10):
                trail = 18 + n*17 + rng.uniform(-5,5)
                sx = tx - slip_dir*trail*.55 + rng.uniform(-10,10)
                sy = ty + trail + rng.uniform(-7,7)
                r = 10 + n*.9 + rng.uniform(0,7)
                d.ellipse([sx-r,sy-r,sx+r,sy+r],fill=(222,225,229,max(18,78-n*5)))
            d.line([(tx,ty),(tx-slip_dir*115,ty+235)],fill=(15,15,17,125),width=10)

        # A faint velocity trail shows that the car is moving in a different direction
        # than the nose is pointing — the visual signature of a drift.
        d.line([(px,py+90),(px-slip_dir*150,py+280)],fill=(255,255,255,28),width=4)
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
        _rotated_car(img,px,py,1.15,drift_angle_deg,True,0)
        d=ImageDraw.Draw(img,"RGBA")
    else:
        _car(d,px,py,1.15,frame.player.heading,True,0)

    # HUD now has a real race stake: viewers can watch Red climb or lose places.
    d.rounded_rectangle([48,52,W-48,250], radius=34, fill=(9,14,21,182), outline=(255,255,255,45), width=2)
    f1=_font(54,True); f2=_font(34,True); fpos=_font(42,True)
    d.text((82,78),f"EP. {episode:03d}",font=f1,fill=(255,255,255,255))
    level=max(1,int(skill*100))
    d.text((82,151),f"DRIVER LEVEL {level}",font=f2,fill=(237,242,248,255))
    d.text((W-330,82),f"{int(frame.player.speed*310):03d} KM/H",font=f2,fill=(255,224,126,255))
    d.text((W-245,145),f"P{frame.position}/{frame.total_cars}",font=fpos,fill=(255,255,255,255))

    bx0,by0,bx1,by1=82,219,W-82,234
    d.rounded_rectangle([bx0,by0,bx1,by1],radius=7,fill=(255,255,255,42))
    d.rounded_rectangle([bx0,by0,bx0+(bx1-bx0)*frame.race_progress,by1],radius=7,fill=(255,213,90,245))

    if frame.event_text:
        text=frame.event_text
        box=d.textbbox((0,0),text,font=f1); tw=box[2]-box[0]
        d.rounded_rectangle([W/2-tw/2-34,330,W/2+tw/2+34,420],radius=24,fill=(0,0,0,178),outline=(255,255,255,34),width=2)
        d.text((W/2-tw/2,346),text,font=f1,fill=(255,255,255,255))

    if frame.race_progress > .93:
        if skill < .42:
            label="NEXT UNLOCK: MOUNTAIN ROAD @ LVL 42"
        elif skill < .56:
            label="NEXT UNLOCK: NIGHT CITY @ LVL 56"
        elif skill < .68:
            label="NEXT UNLOCK: RAIN @ LVL 68"
        else:
            label="NEXT RACE GETS HARDER"
        lf=_font(34,True)
    else:
        label="BEGINNER" if skill<.28 else "GETTING GOOD" if skill<.58 else "PRO"
        lf=f1

    d.rounded_rectangle([60,1740,W-60,1850],radius=30,fill=(8,10,14,205))
    bbox=d.textbbox((0,0),label,font=lf); tw=bbox[2]-bbox[0]
    d.text((W/2-tw/2,1766),label,font=lf,fill=(255,255,255,255))

    if frame.shake>.2:
        overlay=Image.new("RGBA",(W,H),(255,255,255,int(16*min(1.0,frame.shake))))
        img=Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")
    return img
