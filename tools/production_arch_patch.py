from pathlib import Path

# --- race_engine.py: obey showrunner plans + road characteristics ---
p = Path("race_engine.py")
s = p.read_text(encoding="utf-8")

old = '''    featured_rival: str\n    objective_text: str\n'''
new = '''    featured_rival: str\n    objective_text: str\n    track_name: str\n    track_theme: str\n    hook_text: str\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''    def __init__(self, skill: float, seed: int, duration: float = 24.0, fps: int = 30):\n'''
new = '''    def __init__(self, skill: float, seed: int, duration: float = 24.0, fps: int = 30, plan: dict | None = None):\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''        self.held_event: str | None = None\n        self.event_until = -999\n\n        self.target_position = 5 if self.skill < .34 else 4 if self.skill < .58 else 3\n        self.featured_index = seed % len(self.DRIVER_CAST)\n        self.featured_rival = self.DRIVER_CAST[self.featured_index][0]\n        featured_personality = self.DRIVER_CAST[self.featured_index][1]\n        self.objective_text = (\n            f"TARGET P{self.target_position} • {self.featured_rival} "\n            f"{self.PERSONALITY_LINES[featured_personality]}"\n        )\n\n        self.incident_times = [3.1, 6.6, 10.2, 14.0, 17.7, 20.7]\n        self.incident_cursor = 0\n'''
new = '''        self.held_event: str | None = None\n        self.event_until = -999\n        self.plan = plan or {}\n        self.track = dict(self.plan.get("track", {}))\n\n        fallback_target = 5 if self.skill < .34 else 4 if self.skill < .58 else 3\n        self.target_position = int(self.plan.get("target_position", fallback_target))\n        planned_rival = str(self.plan.get("featured_rival", ""))\n        names = [name for name, _ in self.DRIVER_CAST]\n        self.featured_rival = planned_rival if planned_rival in names else names[seed % len(names)]\n        self.featured_index = names.index(self.featured_rival)\n        featured_personality = self.DRIVER_CAST[self.featured_index][1]\n        self.objective_text = str(self.plan.get(\n            "objective_text",\n            f"TARGET P{self.target_position} • {self.featured_rival} {self.PERSONALITY_LINES[featured_personality]}",\n        ))\n        self.hook_text = str(self.plan.get("hook", f"CAN RED REACH P{self.target_position}?"))\n        self.planned_beats = list(self.plan.get("beats", []))\n        self.incident_times = (\n            [float(beat.get("time", 0.0)) for beat in self.planned_beats]\n            if self.planned_beats\n            else [3.1, 6.6, 10.2, 14.0, 17.7, 20.7]\n        )\n        self.incident_cursor = 0\n'''
assert old in s
s = s.replace(old, new, 1)

s = s.replace('''        section_len = 3.25\n''', '''        section_len = float(self.track.get("section_len", 3.25))\n''', 1)
s = s.replace('''        challenge = 0.78 + 0.30 * self.skill\n''', '''        challenge = (0.78 + 0.30 * self.skill) * float(self.track.get("curve_scale", 1.0))\n''', 1)

old = '''    def _difficulty(self, t: float) -> float:\n        ramp = min(1.0, t / max(1.0, self.duration * 0.62))\n        return 0.30 + 0.70 * ramp\n'''
new = '''    def _difficulty(self, t: float) -> float:\n        ramp = min(1.0, t / max(1.0, self.duration * 0.62))\n        base = 0.30 + 0.70 * ramp\n        track_difficulty = float(self.track.get("difficulty", base))\n        return max(0.25, min(1.0, base * (0.82 + 0.28 * track_difficulty)))\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''    def _start_incident(self, rival: RivalState, i: int) -> str:\n'''
new = '''    def _start_incident(self, rival: RivalState, i: int, forced_action: str | None = None) -> str:\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''        behavior = self.rng.choice(choices)\n'''
new = '''        allowed = {"block", "brake_check", "swerve", "spin", "panic", "showboat", "divebomb"}\n        behavior = forced_action if forced_action in allowed else self.rng.choice(choices)\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''        if self.incident_cursor < len(self.incident_times) and t >= self.incident_times[self.incident_cursor]:\n            driver = self._pick_incident_driver()\n            if driver is not None:\n                event = self._start_incident(driver, i)\n                self.last_event = i\n            self.incident_cursor += 1\n'''
new = '''        if self.incident_cursor < len(self.incident_times) and t >= self.incident_times[self.incident_cursor]:\n            beat = self.planned_beats[self.incident_cursor] if self.incident_cursor < len(self.planned_beats) else {}\n            wanted = beat.get("driver")\n            driver = next((r for r in self.rivals if r.active and r.name == wanted), None) if wanted else None\n            if driver is None:\n                driver = self._pick_incident_driver()\n            if driver is not None:\n                event = self._start_incident(driver, i, forced_action=beat.get("action"))\n                if beat.get("caption"):\n                    event = str(beat["caption"])\n                self.last_event = i\n            self.incident_cursor += 1\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''        road_width = 0.86 - abs(curve) * (0.08 + 0.07 * self.skill)\n        road_width = max(0.67, min(0.88, road_width))\n'''
new = '''        road_width = 0.86 - abs(curve) * (0.08 + 0.07 * self.skill)\n        road_width *= float(self.track.get("width_scale", 1.0))\n        road_width = max(0.62, min(0.92, road_width))\n'''
assert old in s
s = s.replace(old, new, 1)

old = '''            featured_rival=self.featured_rival,\n            objective_text=self.objective_text,\n        )\n'''
new = '''            featured_rival=self.featured_rival,\n            objective_text=self.objective_text,\n            track_name=str(self.track.get("name", "Circuit")),\n            track_theme=str(self.track.get("theme", "country")),\n            hook_text=self.hook_text,\n        )\n'''
assert old in s
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# --- renderer.py: visually distinguish road themes + use showrunner hook ---
p = Path("renderer.py")
r = p.read_text(encoding="utf-8")

old = '''    rng=random.Random(frame_no//3)\n    img=Image.new("RGB",(W,H),(116,174,224)); d=ImageDraw.Draw(img,"RGBA")\n\n    for y in range(0,HORIZON,8):\n        p=y/HORIZON\n        d.rectangle([0,y,W,y+8],fill=(int(95+50*p),int(155+48*p),int(220+25*p),255))\n    mountains=[(0,610),(120,500),(235,585),(360,455),(480,565),(620,430),(760,555),(900,470),(1080,585),(1080,760),(0,760)]\n    d.polygon(mountains,fill=(81,111,122,255)); d.rectangle([0,600,W,H],fill=(78,139,72,255))\n'''
new = '''    rng=random.Random(frame_no//3)\n    theme=getattr(frame,"track_theme","country")\n    palettes={\n        "training":((116,174,224),(81,111,122),(78,139,72)),\n        "country":((116,174,224),(81,111,122),(78,139,72)),\n        "mountain":((126,166,205),(72,94,108),(68,111,72)),\n        "night_city":((24,34,66),(31,37,55),(28,38,49)),\n        "rain":((77,101,126),(65,75,87),(60,80,72)),\n        "coast":((92,176,222),(72,116,139),(74,146,123)),\n        "snow":((183,205,226),(135,151,166),(210,218,221)),\n        "canyon":((196,139,100),(122,77,58),(143,89,55)),\n        "desert":((222,177,116),(164,113,72),(190,143,83)),\n        "forest":((83,133,123),(49,77,66),(47,94,59)),\n        "street":((105,124,145),(63,68,76),(70,73,77)),\n        "tunnel":((46,52,65),(36,39,47),(47,48,51)),\n        "neon_rain":((38,31,78),(45,40,69),(34,42,54)),\n        "alpine":((159,190,218),(107,128,144),(184,199,194)),\n        "extreme_canyon":((187,109,77),(105,57,49),(121,69,50)),\n    }\n    sky,mountain_col,ground=palettes.get(theme,palettes["country"])\n    img=Image.new("RGB",(W,H),sky); d=ImageDraw.Draw(img,"RGBA")\n\n    for y in range(0,HORIZON,8):\n        p=y/HORIZON\n        d.rectangle([0,y,W,y+8],fill=(int(sky[0]*(.82+.18*p)),int(sky[1]*(.82+.18*p)),int(sky[2]*(.88+.12*p)),255))\n    mountains=[(0,610),(120,500),(235,585),(360,455),(480,565),(620,430),(760,555),(900,470),(1080,585),(1080,760),(0,760)]\n    d.polygon(mountains,fill=mountain_col+(255,)); d.rectangle([0,600,W,H],fill=ground+(255,))\n    if theme in {"rain","neon_rain"}:\n        for _ in range(90):\n            x=rng.randrange(0,W); y=rng.randrange(0,H); length=rng.randrange(16,42)\n            d.line([(x,y),(x-7,y+length)],fill=(205,225,245,68),width=2)\n    elif theme in {"snow","alpine"}:\n        for _ in range(65):\n            x=rng.randrange(0,W); y=rng.randrange(0,H); rr=rng.randrange(2,6)\n            d.ellipse([x-rr,y-rr,x+rr,y+rr],fill=(245,248,250,135))\n    elif theme in {"night_city","neon_rain","tunnel"}:\n        for x in range(45,W,95):\n            h=rng.randrange(45,170); d.rectangle([x,600-h,x+48,600],fill=(20,24,35,180))\n            if theme!="tunnel":\n                for wy in range(600-h+12,590,24):\n                    d.rectangle([x+8,wy,x+14,wy+7],fill=(255,210,92,145))\n'''
assert old in r
r = r.replace(old, new, 1)

old = '''        hook=f"CAN RED REACH P{frame.target_position}?"\n'''
new = '''        hook=getattr(frame,"hook_text",f"CAN RED REACH P{frame.target_position}?")\n'''
assert old in r
r = r.replace(old, new, 1)

old = '''        rival=f"WATCH {frame.featured_rival}."\n'''
new = '''        rival=f"{getattr(frame,'track_name','CIRCUIT')} • WATCH {frame.featured_rival}"\n'''
assert old in r
r = r.replace(old, new, 1)

p.write_text(r, encoding="utf-8")
