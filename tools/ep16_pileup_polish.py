from pathlib import Path

engine = Path('race_engine.py')
s = engine.read_text()

# 1) Persistent separation state on every car.
s = s.replace(
'''    crash_recovery_timer: int = 0\n''',
'''    crash_recovery_timer: int = 0\n    separation_timer: int = 0\n''',
1,
)
s = s.replace(
'''    slide_velocity: float = 0.0\n\n\n@dataclass\nclass RaceFrame:''',
'''    slide_velocity: float = 0.0\n    separation_timer: int = 0\n\n\n@dataclass\nclass RaceFrame:''',
1,
)

# 2) Held captions so a crash/pileup is readable for more than a single frame.
s = s.replace(
'''        self.crash_chain_hits = 0\n        self.crash_chain_until = -999\n''',
'''        self.crash_chain_hits = 0\n        self.crash_chain_until = -999\n        self.held_event: str | None = None\n        self.event_until = -999\n''',
1,
)

anchor = '''    def _record_crash_chain(self, i: int, strength: float) -> str | None:\n'''
insert = '''    def _hold_event(self, text: str | None, i: int) -> str | None:\n        if text:\n            major = any(word in text for word in ("PILEUP", "CRASH", "HUGE HIT", "FULL SPIN", "BIG CONTACT"))\n            hold = 1.05 if major else 0.62\n            self.held_event = text\n            self.event_until = i + int(self.fps * hold)\n            return text\n        if self.held_event and i <= self.event_until:\n            return self.held_event\n        return None\n\n    def _record_crash_chain(self, i: int, strength: float) -> str | None:\n'''
assert anchor in s
s = s.replace(anchor, insert, 1)

# Keep a chain alive long enough for a third car to arrive.
s = s.replace(
'''        self.crash_chain_until = i + int(self.fps * 0.85)\n''',
'''        self.crash_chain_until = i + int(self.fps * 1.20)\n''',
1,
)

# 3) Cluster solver: repeated positional projection after impulses have already fired.
anchor = '''    def _resolve_rival_contacts(self, i: int) -> str | None:\n'''
cluster = '''    def _separate_crash_clusters(self) -> int:\n        """Project overlapping crash bodies apart without cancelling real impacts.\n\n        Contact impulses run first. This method then performs several cheap positional\n        correction passes, which matters when 3+ cars are in the same incident and a\n        pair-by-pair solver would otherwise leave one pair visually intersecting.\n        """\n        crash_states = {"spin", "big_spin", "aftermath", "recover", "late_react", "avoid_crash"}\n        active = [r for r in self.rivals if r.active]\n        player_z = 1.01\n        cluster_members: set[str] = set()\n\n        for _ in range(4):\n            for ai in range(len(active)):\n                for bi in range(ai + 1, len(active)):\n                    a, b = active[ai], active[bi]\n                    involved = (\n                        a.separation_timer > 0 or b.separation_timer > 0\n                        or a.behavior in crash_states or b.behavior in crash_states\n                        or a.contact_strength >= 0.72 or b.contact_strength >= 0.72\n                    )\n                    if not involved:\n                        continue\n                    dz = abs(a.z - b.z)\n                    dl = abs(a.lane - b.lane)\n                    if dz >= 0.072 or dl >= 0.178:\n                        continue\n\n                    cluster_members.update((a.name, b.name))\n                    side = self._contact_side(a.lane, b.lane, 1.0 if a.color < b.color else -1.0)\n                    lane_overlap = max(0.0, 0.178 - dl)\n                    z_overlap = max(0.0, 0.072 - dz)\n                    lateral = lane_overlap * 0.52 + 0.0025\n                    a.lane = max(-0.82, min(0.82, a.lane - side * lateral))\n                    b.lane = max(-0.82, min(0.82, b.lane + side * lateral))\n                    if a.z <= b.z:\n                        a.z -= z_overlap * 0.52\n                        b.z += z_overlap * 0.52\n                    else:\n                        b.z -= z_overlap * 0.52\n                        a.z += z_overlap * 0.52\n\n            for rival in active:\n                involved = (\n                    self.player.separation_timer > 0 or rival.separation_timer > 0\n                    or self.player.crashed or rival.behavior in crash_states\n                    or self.player.contact_strength >= 0.72 or rival.contact_strength >= 0.72\n                )\n                if not involved:\n                    continue\n                dz = abs(rival.z - player_z)\n                dl = abs(rival.lane - self.player.lane)\n                if dz >= 0.070 or dl >= 0.172:\n                    continue\n\n                cluster_members.update(("RED", rival.name))\n                side = self._contact_side(self.player.lane, rival.lane, 1.0 if rival.color % 2 == 0 else -1.0)\n                lane_overlap = max(0.0, 0.172 - dl)\n                z_overlap = max(0.0, 0.070 - dz)\n                lateral = lane_overlap * 0.48 + 0.0025\n                self.player.lane = max(-0.82, min(0.82, self.player.lane - side * lateral))\n                rival.lane = max(-0.82, min(0.82, rival.lane + side * lateral))\n                # RED's camera plane is fixed, so move the rival longitudinally.\n                rival.z += (-z_overlap if rival.z < player_z else z_overlap) * 0.92\n\n        return len(cluster_members)\n\n    def _resolve_rival_contacts(self, i: int) -> str | None:\n'''
assert anchor in s
s = s.replace(anchor, cluster, 1)

# 4) Hard impacts enter a short separation state so they don't immediately re-merge.
s = s.replace(
'''                a.contact_strength = b.contact_strength = strength\n                a.heading -= side_a * heading_impulse\n''',
'''                a.contact_strength = b.contact_strength = strength\n                if strength >= 0.72:\n                    sep = int(self.fps * (0.42 if strength >= 0.90 else 0.26))\n                    a.separation_timer = max(a.separation_timer, sep)\n                    b.separation_timer = max(b.separation_timer, sep)\n                a.heading -= side_a * heading_impulse\n''',
1,
)
s = s.replace(
'''            rival.contact_strength = strength\n            self.player.heading -= side_red * heading_impulse\n''',
'''            rival.contact_strength = strength\n            if strength >= 0.72:\n                sep = int(self.fps * (0.44 if strength >= 0.93 else 0.27))\n                self.player.separation_timer = max(self.player.separation_timer, sep)\n                rival.separation_timer = max(rival.separation_timer, sep)\n            self.player.heading -= side_red * heading_impulse\n''',
1,
)

# 5) Decay separation timers once per frame.
s = s.replace(
'''        if self.player.contact_timer > 0:\n            self.player.contact_timer -= 1\n''',
'''        if self.player.separation_timer > 0:\n            self.player.separation_timer -= 1\n\n        if self.player.contact_timer > 0:\n            self.player.contact_timer -= 1\n''',
1,
)
s = s.replace(
'''        for rival in self.rivals:\n            prev_z = rival.z\n            if rival.contact_timer > 0:\n''',
'''        for rival in self.rivals:\n            prev_z = rival.z\n            if rival.separation_timer > 0:\n                rival.separation_timer -= 1\n            if rival.contact_timer > 0:\n''',
1,
)

# 6) Crash avoidance is more readable: avoiders brake harder, late reactors stay committed.
s = s.replace(
'''                elif rival.behavior == "avoid_crash":\n                    rival.speed += (rival.base_speed * 0.68 - rival.speed) * 0.15\n                elif rival.behavior == "late_react":\n                    rival.speed += (rival.base_speed * 0.90 - rival.speed) * 0.08\n                    rival.heading += math.sin(i * 0.41) * 0.012\n''',
'''                elif rival.behavior == "avoid_crash":\n                    rival.speed += (rival.base_speed * 0.54 - rival.speed) * 0.18\n                    rival.heading = max(-0.24, min(0.24, (rival.target_lane - rival.lane) * 0.42))\n                elif rival.behavior == "late_react":\n                    # Too late to fully avoid it: small brake lift, mostly holds the line.\n                    rival.speed += (rival.base_speed * 0.82 - rival.speed) * 0.10\n                    rival.heading += math.sin(i * 0.41) * 0.010\n''',
1,
)

# 7) Run projection after all contact impulses and mark a real 3+ car cluster.
anchor = '''        player_contact_event = self._resolve_player_contacts(i)\n        if player_contact_event:\n            event = player_contact_event\n            shake = max(shake, 0.16 + self.player.contact_strength * 0.12)\n\n        road_width = 0.86 - abs(curve) * (0.08 + 0.07 * self.skill)\n'''
replacement = '''        player_contact_event = self._resolve_player_contacts(i)\n        if player_contact_event:\n            event = player_contact_event\n            shake = max(shake, 0.16 + self.player.contact_strength * 0.12)\n\n        cluster_size = self._separate_crash_clusters()\n        if cluster_size >= 3 and i <= self.crash_chain_until and i - self.last_event > int(self.fps * 0.35):\n            event = f"{cluster_size}-CAR PILEUP! 😭"\n            self.last_event = i\n\n        road_width = 0.86 - abs(curve) * (0.08 + 0.07 * self.skill)\n'''
assert anchor in s
s = s.replace(anchor, replacement, 1)

# 8) Hold important captions. Finish messages still override because they're assigned first.
anchor = '''        return RaceFrame(\n            t=t,\n'''
replacement = '''        event = self._hold_event(event, i)\n\n        return RaceFrame(\n            t=t,\n'''
assert anchor in s
s = s.replace(anchor, replacement, 1)

engine.write_text(s)

# Renderer: make aftermath more readable without adding HUD clutter.
renderer = Path('renderer.py')
r = renderer.read_text()

# Avoiding cars show brake lights as part of the reaction.
r = r.replace(
'''        if rival.behavior in {"panic","brake_check"}:\n''',
'''        if rival.behavior in {"panic","brake_check","avoid_crash"}:\n''',
1,
)

# More persistent smoke for actual pileup states and small debris flecks.
old = '''            smoke_count=16 if rival.behavior=="big_spin" else 10 if rival.behavior=="aftermath" else 7\n            for _ in range(smoke_count):\n                rr=rng.uniform(6,19)*scale; sx=x+rng.uniform(-42,42)*scale; sy=y+rng.uniform(28,110)*scale\n                alpha=rng.randint(40,105) if rival.behavior=="big_spin" else rng.randint(35,90)\n                d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,alpha))\n'''
new = '''            smoke_count=18 if rival.behavior=="big_spin" else 13 if rival.behavior=="aftermath" else 8\n            for _ in range(smoke_count):\n                rr=rng.uniform(6,21)*scale; sx=x+rng.uniform(-46,46)*scale; sy=y+rng.uniform(28,118)*scale\n                alpha=rng.randint(45,112) if rival.behavior=="big_spin" else rng.randint(38,94)\n                d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,alpha))\n            if rival.behavior in {"big_spin","aftermath"}:\n                for _ in range(5):\n                    ox=rng.uniform(-58,58)*scale; oy=rng.uniform(30,105)*scale; rr=rng.uniform(2,5)*scale\n                    d.rectangle([x+ox-rr,y+oy-rr,x+ox+rr,y+oy+rr],fill=rng.choice([(42,42,45,150),(92,96,101,135),(245,173,68,145)]))\n'''
assert old in r
r = r.replace(old, new, 1)

# Player crash smoke/debris should persist clearly through the rejoin beat.
old = '''        for _ in range(14):\n            rr=rng.uniform(10,26); sx=px+rng.uniform(-65,65); sy=py+rng.uniform(45,155)\n            d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,rng.randint(35,90)))\n'''
new = '''        for _ in range(18):\n            rr=rng.uniform(10,28); sx=px+rng.uniform(-72,72); sy=py+rng.uniform(42,165)\n            d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,rng.randint(38,96)))\n        for _ in range(6):\n            ox=rng.uniform(-72,72); oy=rng.uniform(45,145); rr=rng.uniform(2,5)\n            d.rectangle([px+ox-rr,py+oy-rr,px+ox+rr,py+oy+rr],fill=rng.choice([(45,45,48,155),(105,108,112,140),(246,172,65,150)]))\n'''
assert old in r
r = r.replace(old, new, 1)

renderer.write_text(r)
print('EP16 pileup polish applied')
