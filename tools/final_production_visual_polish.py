from pathlib import Path

p = Path("renderer.py")
s = p.read_text(encoding="utf-8")

old = '''        grass=(72,132,67,255) if j%2 else (76,143,70,255)\n        d.polygon([(0,y0),(W,y0),(W,y1),(0,y1)],fill=grass)\n'''
new = '''        ground_mul = 0.94 if j % 2 else 1.03\n        roadside = tuple(max(0, min(255, int(c * ground_mul))) for c in ground) + (255,)\n        d.polygon([(0,y0),(W,y0),(W,y1),(0,y1)],fill=roadside)\n'''
assert old in s, "roadside anchor missing"
s = s.replace(old, new, 1)

old = '''        hook=getattr(frame,"hook_text",f"CAN RED REACH P{frame.target_position}?")\n        bb=d.textbbox((0,0),hook,font=title); d.text((W/2-(bb[2]-bb[0])/2,1300),hook,font=title,fill=(255,255,255,alpha))\n'''
new = '''        hook=getattr(frame,"hook_text",f"CAN RED REACH P{frame.target_position}?")\n        hook_font=title\n        bb=d.textbbox((0,0),hook,font=hook_font)\n        if bb[2]-bb[0] > 820:\n            hook_font=_font(46,True); bb=d.textbbox((0,0),hook,font=hook_font)\n        if bb[2]-bb[0] > 820:\n            hook_font=_font(38,True); bb=d.textbbox((0,0),hook,font=hook_font)\n        d.text((W/2-(bb[2]-bb[0])/2,1300),hook,font=hook_font,fill=(255,255,255,alpha))\n'''
assert old in s, "hook anchor missing"
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
