from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RACE = ROOT / "race_engine.py"
RENDER = ROOT / "renderer.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing replacement target: {label}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, new_block: str, label: str) -> str:
    i = text.find(start)
    if i < 0:
        raise RuntimeError(f"missing start marker: {label}")
    j = text.find(end, i)
    if j < 0:
        raise RuntimeError(f"missing end marker: {label}")
    return text[:i] + new_block.rstrip() + "\n\n" + text[j:]


def commit(message: str):
    subprocess.run(["git", "add", "race_engine.py", "renderer.py"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)


# -----------------------------------------------------------------------------
# STAGE 1 — HARD IMPACTS: full spins, momentum loss, sideways slide, recovery.
# -----------------------------------------------------------------------------
race = RACE.read_text()
render = RENDER.read_text()

race = replace_once(
    race,
    "    contact_strength: float = 0.0\n\n\n@dataclass\nclass RivalState:",
    "    contact_strength: float = 0.0\n    crash_rotation: float = 0.0\n    crash_spin_rate: float = 0.0\n    crash_slide_velocity: float = 0.0\n\n\n@dataclass\nclass RivalState:",
    "player crash spin fields",
)

new_spin_helpers = '''    def _kick_spin(self, rival: RivalState, direction: float | None = None,
                   severity: float = 0.8, full_spin: bool = False):
        """Kick a rival into a real loss-of-control state.

        Normal spin-outs rotate sideways and recover. Hard impacts can trigger a full
        180–360 degree spin, but forward speed collapses while the car is facing the
        wrong way so it never appears to drive backwards down the circuit.
        """
        if direction is None or abs(direction) < 0.1:
            direction = self.rng.choice([-1.0, 1.0])
        direction = 1.0 if direction > 0 else -1.0
        severity = max(0.2, min(1.0, severity))

        rival.behavior = "big_spin" if full_spin else "spin"
        if full_spin:
            rival.behavior_timer = max(
                rival.behavior_timer,
                int(self.fps * (1.22 + 0.30 * severity)),
            )
            rival.spin_rate = direction * (0.155 + 0.045 * severity)
            rival.slide_velocity = direction * (0.011 + 0.008 * severity)
            rival.rotation += direction * 0.08
            rival.speed *= 0.58
        else:
            rival.behavior_timer = max(
                rival.behavior_timer,
                int(self.fps * (0.78 + 0.34 * severity)),
            )
            rival.spin_rate = direction * (0.050 + 0.020 * severity)
            rival.slide_velocity = direction * (0.007 + 0.006 * severity)
            rival.rotation += direction * (0.08 + 0.08 * severity)
            rival.rotation = max(-1.05, min(1.05, rival.rotation))
        rival.target_lane = rival.lane

    def _kick_player_crash(self, direction: float, severity: float):
        """Hard player contact gets the same momentum-aware spin treatment."""
        direction = 1.0 if direction >= 0 else -1.0
        severity = max(0.2, min(1.0, severity))
        self.player.crashed = True
        self.player.crash_timer = max(
            self.player.crash_timer,
            int(self.fps * (1.05 + 0.30 * severity)),
        )
        self.player.crash_spin_rate = direction * (0.165 + 0.045 * severity)
        self.player.crash_slide_velocity = direction * (0.010 + 0.008 * severity)
        self.player.crash_rotation += direction * 0.08
        self.player.speed *= 0.56
'''
race = replace_between(
    race,
    "    def _kick_spin",
    "    def _start_incident",
    new_spin_helpers,
    "spin helpers",
)

race = replace_once(
    race,
    '''                if strength > 0.67:\n                    victim = a if self.rng.random() < 0.5 else b\n                    direction = victim.contact_side\n                    self._kick_spin(victim, direction=direction, severity=strength)\n''',
    '''                if strength > 0.88:\n                    victim = a if self.rng.random() < 0.5 else b\n                    self._kick_spin(\n                        victim, direction=victim.contact_side, severity=strength, full_spin=True\n                    )\n                elif strength > 0.67:\n                    victim = a if self.rng.random() < 0.5 else b\n                    self._kick_spin(victim, direction=victim.contact_side, severity=strength)\n''',
    "hard rival contact threshold",
)

race = replace_once(
    race,
    '''            if strength > 0.72:\n                if reckless or self.rng.random() < 0.68:\n                    self._kick_spin(rival, direction=side_rival, severity=strength)\n                elif not self.player.crashed:\n                    self.player.crashed = True\n                    self.player.crash_timer = self.rng.randint(12, 22)\n''',
    '''            if strength > 0.90:\n                if reckless and self.rng.random() < 0.72:\n                    self._kick_spin(\n                        rival, direction=side_rival, severity=strength, full_spin=True\n                    )\n                elif not self.player.crashed:\n                    self._kick_player_crash(side_red, strength)\n            elif strength > 0.72:\n                if reckless or self.rng.random() < 0.68:\n                    self._kick_spin(rival, direction=side_rival, severity=strength)\n                elif not self.player.crashed:\n                    self.player.crashed = True\n                    self.player.crash_timer = self.rng.randint(12, 22)\n''',
    "hard player contact threshold",
)

race = replace_once(
    race,
    '''                elif rival.behavior == "spin":\n                    # A spin is now a real loss-of-control state. The car slows hard,\n                    # slides sideways and reaches at most ~74 degrees before recovery.\n                    spin_target_speed = max(0.09, rival.base_speed * 0.18)\n                    rival.speed += (spin_target_speed - rival.speed) * 0.17\n                    rival.lane += rival.slide_velocity\n                    rival.slide_velocity *= 0.945\n\n                    if rival.behavior_timer > int(self.fps * 0.42):\n                        rival.rotation += rival.spin_rate\n                        rival.spin_rate *= 0.965\n                        if abs(rival.rotation) >= 1.05:\n                            rival.rotation = math.copysign(1.05, rival.rotation)\n                            rival.spin_rate *= 0.30\n                    else:\n                        # Recovery starts while the car is still slow. It cannot resume\n                        # normal race pace until its nose points down-track again.\n                        rival.spin_rate *= 0.68\n                        rival.rotation *= 0.80\n                        rival.slide_velocity *= 0.82\n                    rival.target_lane = rival.lane\n                    rival.heading *= 0.75\n                elif rival.behavior == "recover":\n''',
    '''                elif rival.behavior == "spin":\n                    spin_target_speed = max(0.09, rival.base_speed * 0.18)\n                    rival.speed += (spin_target_speed - rival.speed) * 0.17\n                    rival.lane += rival.slide_velocity\n                    rival.slide_velocity *= 0.945\n                    if rival.behavior_timer > int(self.fps * 0.42):\n                        rival.rotation += rival.spin_rate\n                        rival.spin_rate *= 0.965\n                        if abs(rival.rotation) >= 1.05:\n                            rival.rotation = math.copysign(1.05, rival.rotation)\n                            rival.spin_rate *= 0.30\n                    else:\n                        rival.spin_rate *= 0.68\n                        rival.rotation *= 0.80\n                        rival.slide_velocity *= 0.82\n                    rival.target_lane = rival.lane\n                    rival.heading *= 0.75\n                elif rival.behavior == "big_spin":\n                    # Full crash spin. The nose can pass through 180/360 degrees, but\n                    # the car is nearly stopped and sliding while that happens.\n                    spin_target_speed = max(0.055, rival.base_speed * 0.10)\n                    rival.speed += (spin_target_speed - rival.speed) * 0.20\n                    rival.lane += rival.slide_velocity\n                    rival.slide_velocity *= 0.952\n                    if rival.behavior_timer > int(self.fps * 0.38):\n                        rival.rotation += rival.spin_rate\n                        rival.spin_rate *= 0.991\n                    else:\n                        turn = 360.0 / 70.0\n                        rival.rotation = ((rival.rotation + turn / 2) % turn) - turn / 2\n                        rival.rotation *= 0.74\n                        rival.spin_rate *= 0.60\n                        rival.slide_velocity *= 0.78\n                    rival.target_lane = rival.lane\n                    rival.heading *= 0.62\n                elif rival.behavior == "recover":\n''',
    "big spin behavior",
)

race = replace_once(
    race,
    '''                if rival.behavior == "spin":\n                    rival.behavior = "recover"\n                    rival.behavior_timer = int(self.fps * 0.50)\n                    rival.spin_rate *= 0.45\n                    rival.slide_velocity *= 0.55\n                elif rival.behavior == "recover":\n''',
    '''                if rival.behavior in {"spin", "big_spin"}:\n                    turn = 360.0 / 70.0\n                    rival.rotation = ((rival.rotation + turn / 2) % turn) - turn / 2\n                    rival.behavior = "recover"\n                    rival.behavior_timer = int(self.fps * 0.55)\n                    rival.spin_rate *= 0.40\n                    rival.slide_velocity *= 0.50\n                elif rival.behavior == "recover":\n''',
    "spin to recovery",
)

race = race.replace('rival.behavior not in {"spin", "recover"}', 'rival.behavior not in {"spin", "big_spin", "recover"}')
race = race.replace('r.behavior not in {"spin", "recover"}', 'r.behavior not in {"spin", "big_spin", "recover"}')

race = replace_once(
    race,
    '''        if self.player.crashed:\n            self.player.speed *= 0.966\n            self.player.heading *= 0.91\n            self.player.crash_timer -= 1\n            self.player.drifting = False\n            self.player.drift_angle *= 0.8\n            self.player.drift_slip *= 0.75\n            shake = max(shake, min(0.38, max(0.0, self.player.crash_timer / 85.0)))\n            if self.player.crash_timer <= 0:\n                self.player.crashed = False\n                self.player.lane *= 0.65\n                self.player.speed = 0.34\n                event = "RED'S BACK!"\n                self.last_event = i\n''',
    '''        if self.player.crashed:\n            self.player.crash_timer -= 1\n            self.player.drifting = False\n            self.player.drift_angle *= 0.8\n            self.player.drift_slip *= 0.75\n            if abs(self.player.crash_spin_rate) > 0.002:\n                crash_target_speed = 0.07\n                self.player.speed += (crash_target_speed - self.player.speed) * 0.18\n                self.player.lane += self.player.crash_slide_velocity\n                self.player.crash_slide_velocity *= 0.95\n                if self.player.crash_timer > int(self.fps * 0.34):\n                    self.player.crash_rotation += self.player.crash_spin_rate\n                    self.player.crash_spin_rate *= 0.991\n                else:\n                    turn = 360.0 / 70.0\n                    self.player.crash_rotation = (\n                        (self.player.crash_rotation + turn / 2) % turn\n                    ) - turn / 2\n                    self.player.crash_rotation *= 0.72\n                    self.player.crash_spin_rate *= 0.58\n                    self.player.crash_slide_velocity *= 0.76\n            else:\n                self.player.speed *= 0.966\n                self.player.heading *= 0.91\n            self.player.lane = max(-0.82, min(0.82, self.player.lane))\n            shake = max(shake, min(0.38, max(0.0, self.player.crash_timer / 85.0)))\n            if self.player.crash_timer <= 0:\n                self.player.crashed = False\n                self.player.lane *= 0.65\n                self.player.speed = max(0.30, self.player.speed)\n                self.player.crash_rotation = 0.0\n                self.player.crash_spin_rate = 0.0\n                self.player.crash_slide_velocity = 0.0\n                event = "RED'S BACK!"\n                self.last_event = i\n''',
    "player hard crash motion",
)

render = replace_once(
    render,
    '''        if rival.behavior=="spin" or abs(rival.rotation)>.10:\n            _rotated_car(img,x,y,scale,rival.rotation*70.0+contact_angle,False,rival.color)\n            d=ImageDraw.Draw(img,"RGBA")\n            for _ in range(7):\n                rr=rng.uniform(6,17)*scale; sx=x+rng.uniform(-32,32)*scale; sy=y+rng.uniform(30,92)*scale\n                d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,rng.randint(35,90)))\n''',
    '''        if rival.behavior in {"spin","big_spin","recover"} or abs(rival.rotation)>.10:\n            _rotated_car(img,x,y,scale,rival.rotation*70.0+contact_angle,False,rival.color)\n            d=ImageDraw.Draw(img,"RGBA")\n            smoke_count=16 if rival.behavior=="big_spin" else 7\n            for _ in range(smoke_count):\n                rr=rng.uniform(6,19)*scale; sx=x+rng.uniform(-42,42)*scale; sy=y+rng.uniform(28,110)*scale\n                alpha=rng.randint(40,105) if rival.behavior=="big_spin" else rng.randint(35,90)\n                d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,alpha))\n            if rival.behavior=="big_spin":\n                d.line([(x-38*scale,y+55*scale),(x-rival.slide_velocity*9000,y+145*scale)],fill=(15,15,17,120),width=max(4,int(8*scale)))\n                d.line([(x+38*scale,y+55*scale),(x-rival.slide_velocity*9000+76*scale,y+145*scale)],fill=(15,15,17,120),width=max(4,int(8*scale)))\n''',
    "hard spin rendering",
)

render = replace_once(
    render,
    '''    if frame.player.drifting and abs(frame.player.drift_angle)>.08:\n        _rotated_car(img,px,py,1.15,drift_angle_deg+player_contact_angle,True,0); d=ImageDraw.Draw(img,"RGBA")\n    elif frame.player.contact_timer>0:\n        _rotated_car(img,px,py,1.15,player_contact_angle,True,0); d=ImageDraw.Draw(img,"RGBA")\n    else:\n        _car(d,px,py,1.15,frame.player.heading,True,0)\n''',
    '''    if frame.player.crashed and abs(frame.player.crash_rotation)>.03:\n        _rotated_car(img,px,py,1.15,frame.player.crash_rotation*70.0+player_contact_angle,True,0); d=ImageDraw.Draw(img,"RGBA")\n        for _ in range(14):\n            rr=rng.uniform(10,26); sx=px+rng.uniform(-65,65); sy=py+rng.uniform(45,155)\n            d.ellipse([sx-rr,sy-rr,sx+rr,sy+rr],fill=(220,224,228,rng.randint(35,90)))\n    elif frame.player.drifting and abs(frame.player.drift_angle)>.08:\n        _rotated_car(img,px,py,1.15,drift_angle_deg+player_contact_angle,True,0); d=ImageDraw.Draw(img,"RGBA")\n    elif frame.player.contact_timer>0:\n        _rotated_car(img,px,py,1.15,player_contact_angle,True,0); d=ImageDraw.Draw(img,"RGBA")\n    else:\n        _car(d,px,py,1.15,frame.player.heading,True,0)\n''',
    "player hard spin rendering",
)

RACE.write_text(race)
RENDER.write_text(render)
commit("Add full-spin physics for hard impacts")


# -----------------------------------------------------------------------------
# STAGE 2 — LIGHT CONTACT: subtle wheel rubs, less jitter, no spark explosion.
# -----------------------------------------------------------------------------
race = RACE.read_text()
render = RENDER.read_text()

new_rival_contacts = '''    def _resolve_rival_contacts(self, i: int) -> str | None:
        event = None
        active = [r for r in self.rivals if r.active]
        car_len = 0.060
        car_width = 0.155

        for a_idx in range(len(active)):
            for b_idx in range(a_idx + 1, len(active)):
                a, b = active[a_idx], active[b_idx]
                dz = abs(a.z - b.z)
                dl = abs(a.lane - b.lane)
                if dz >= car_len or dl >= car_width:
                    continue

                side_a = self._contact_side(a.lane, b.lane, 1.0 if a_idx % 2 == 0 else -1.0)
                side_b = -side_a
                lane_overlap = car_width - dl
                z_overlap = car_len - dz
                fresh_contact = a.contact_timer <= 0 or b.contact_timer <= 0

                # During an existing rub, only keep the bodies separated. Reapplying a
                # full impulse every frame is what made light contact look jittery.
                if not fresh_contact:
                    push = lane_overlap * 0.18 + 0.001
                    a.lane = max(-0.80, min(0.80, a.lane - side_a * push))
                    b.lane = max(-0.80, min(0.80, b.lane - side_b * push))
                    continue

                relative_speed = abs(a.speed - b.speed)
                reckless = (
                    a.behavior in {"divebomb", "swerve", "showboat", "spin", "big_spin"}
                    or b.behavior in {"divebomb", "swerve", "showboat", "spin", "big_spin"}
                )
                strength = min(1.0, 0.14 + relative_speed * 2.6 + (0.25 if reckless else 0.0))

                if strength < 0.48:
                    push = lane_overlap * 0.30 + 0.002
                    timer = int(self.fps * 0.12)
                    heading_impulse = 0.012 + strength * 0.025
                    speed_keep = 0.998 - strength * 0.004
                    mix = 0.08
                elif strength < 0.82:
                    push = lane_overlap * 0.44 + 0.004
                    timer = int(self.fps * 0.20)
                    heading_impulse = 0.026 + strength * 0.050
                    speed_keep = 0.992 - strength * 0.010
                    mix = 0.20
                else:
                    push = lane_overlap * 0.56 + 0.006
                    timer = int(self.fps * 0.30)
                    heading_impulse = 0.045 + strength * 0.080
                    speed_keep = 0.978 - strength * 0.018
                    mix = 0.36

                a.lane = max(-0.80, min(0.80, a.lane - side_a * push))
                b.lane = max(-0.80, min(0.80, b.lane - side_b * push))
                if a.z <= b.z:
                    a.z -= z_overlap * 0.20
                    b.z += z_overlap * 0.20
                else:
                    b.z -= z_overlap * 0.20
                    a.z += z_overlap * 0.20

                a.contact_timer = b.contact_timer = timer
                a.contact_side, b.contact_side = side_a, side_b
                a.contact_strength = b.contact_strength = strength
                a.heading -= side_a * heading_impulse
                b.heading -= side_b * heading_impulse
                mean_speed = (a.speed + b.speed) * 0.5
                a.speed += (mean_speed - a.speed) * mix
                b.speed += (mean_speed - b.speed) * mix
                a.speed *= speed_keep
                b.speed *= speed_keep

                if strength > 0.90:
                    victim = a if self.rng.random() < 0.5 else b
                    self._kick_spin(victim, victim.contact_side, strength, full_spin=True)
                elif strength > 0.72:
                    victim = a if self.rng.random() < 0.5 else b
                    self._kick_spin(victim, victim.contact_side, strength)

                if i - self.last_event > self.fps * 0.48:
                    if strength > 0.90:
                        event = self.rng.choice(["HUGE HIT! 💥", "FULL SPIN!", "THAT'S A CRASH!"])
                    elif strength >= 0.48:
                        event = self.rng.choice(["WHEEL TO WHEEL!", "THEY TOUCH!", "NO ROOM!"])
                    elif strength > 0.34 and self.rng.random() < 0.35:
                        event = "RUBBING WHEELS"
                    if event:
                        self.last_event = i
        return event
'''
race = replace_between(
    race,
    "    def _resolve_rival_contacts",
    "    def _resolve_player_contacts",
    new_rival_contacts,
    "natural rival contact",
)

new_player_contacts = '''    def _resolve_player_contacts(self, i: int) -> str | None:
        event = None
        car_len = 0.058
        car_width = 0.150
        player_z = 1.01

        for rival in self.rivals:
            if not rival.active:
                continue
            dz = abs(rival.z - player_z)
            dl = abs(rival.lane - self.player.lane)
            if dz >= car_len or dl >= car_width:
                continue

            side_red = self._contact_side(self.player.lane, rival.lane, 1.0 if rival.color % 2 == 0 else -1.0)
            side_rival = -side_red
            lane_overlap = car_width - dl
            fresh_contact = self.player.contact_timer <= 0 or rival.contact_timer <= 0

            if not fresh_contact:
                push = lane_overlap * 0.18 + 0.001
                self.player.lane = max(-0.80, min(0.80, self.player.lane - side_red * push))
                rival.lane = max(-0.80, min(0.80, rival.lane - side_rival * push))
                continue

            relative_speed = abs(self.player.speed - rival.speed)
            reckless = rival.behavior in {"divebomb", "swerve", "block", "brake_check", "showboat", "big_spin"}
            strength = min(1.0, 0.15 + relative_speed * 2.8 + (0.28 if reckless else 0.0))

            if strength < 0.48:
                push = lane_overlap * 0.30 + 0.002
                timer = int(self.fps * 0.12)
                heading_impulse = 0.014 + strength * 0.026
                player_keep = 0.998 - strength * 0.004
                rival_keep = 0.998 - strength * 0.003
            elif strength < 0.84:
                push = lane_overlap * 0.45 + 0.004
                timer = int(self.fps * 0.21)
                heading_impulse = 0.030 + strength * 0.055
                player_keep = 0.991 - strength * 0.011
                rival_keep = 0.992 - strength * 0.010
            else:
                push = lane_overlap * 0.57 + 0.007
                timer = int(self.fps * 0.30)
                heading_impulse = 0.050 + strength * 0.085
                player_keep = 0.976 - strength * 0.020
                rival_keep = 0.978 - strength * 0.018

            self.player.lane = max(-0.80, min(0.80, self.player.lane - side_red * push))
            rival.lane = max(-0.80, min(0.80, rival.lane - side_rival * push))
            if rival.z < player_z:
                rival.z = min(rival.z, player_z - car_len)
            else:
                rival.z = max(rival.z, player_z + car_len)

            self.player.contact_timer = timer
            self.player.contact_side = side_red
            self.player.contact_strength = strength
            rival.contact_timer = timer
            rival.contact_side = side_rival
            rival.contact_strength = strength
            self.player.heading -= side_red * heading_impulse
            rival.heading -= side_rival * heading_impulse
            self.player.speed *= player_keep
            rival.speed *= rival_keep

            if strength > 0.93:
                if reckless and self.rng.random() < 0.72:
                    self._kick_spin(rival, side_rival, strength, full_spin=True)
                elif not self.player.crashed:
                    self._kick_player_crash(side_red, strength)
            elif strength > 0.76:
                if reckless or self.rng.random() < 0.66:
                    self._kick_spin(rival, side_rival, strength)
                elif not self.player.crashed:
                    self.player.crashed = True
                    self.player.crash_timer = self.rng.randint(12, 22)

            if i - self.last_event > self.fps * 0.42:
                if strength > 0.93:
                    event = f"RED AND {rival.name} CRASH! 💥" if rival.name == self.featured_rival else "BIG CONTACT! 💥"
                elif strength >= 0.48:
                    event = f"RED AND {rival.name} MAKE CONTACT!" if rival.name == self.featured_rival else self.rng.choice(["WHEEL TO WHEEL!", "RED RUBS WHEELS!", "NO SPACE!"])
                elif rival.name == self.featured_rival and self.rng.random() < 0.40:
                    event = f"RED RUBS {rival.name}'S WHEEL"
                if event:
                    self.last_event = i
        return event
'''
race = replace_between(
    race,
    "    def _resolve_player_contacts",
    "    def frame",
    new_player_contacts,
    "natural player contact",
)

new_contact_fx = '''def _draw_contact_sparks(d: ImageDraw.ImageDraw, rng: random.Random, x: float, y: float,
                         scale: float, side: float, strength: float):
    # Sparks belong to meaningful metal/carbon contact, not every tiny wheel rub.
    if strength < 0.48:
        return
    sx = x + side * 54 * scale
    sy = y + 10 * scale
    count = max(3, int(3 + (strength - 0.45) * 13))
    for _ in range(count):
        length = rng.uniform(10, 36) * scale * (0.65 + strength)
        angle = rng.uniform(-0.70, 0.70) + (0 if side > 0 else math.pi)
        ex = sx + math.cos(angle) * length
        ey = sy + math.sin(angle) * length + rng.uniform(4, 18) * scale
        color = rng.choice([(255,230,120,245),(255,167,58,245),(255,248,205,235)])
        d.line([(sx,sy),(ex,ey)], fill=color, width=max(2,int(2.5*scale)))
        rr=max(2,2.5*scale)
        d.ellipse([ex-rr,ey-rr,ex+rr,ey+rr],fill=color)


def _draw_tire_scrub(d: ImageDraw.ImageDraw, rng: random.Random, x: float, y: float,
                     scale: float, side: float, strength: float):
    if strength <= 0.04 or strength >= 0.48:
        return
    sx=x+side*50*scale
    sy=y+48*scale
    for _ in range(2 + int(strength*5)):
        rr=rng.uniform(3,7)*scale
        ox=rng.uniform(-8,8)*scale
        oy=rng.uniform(0,18)*scale
        d.ellipse([sx+ox-rr,sy+oy-rr,sx+ox+rr,sy+oy+rr],fill=(205,210,215,45))
'''
render = replace_between(
    render,
    "def _draw_contact_sparks",
    "def render_frame",
    new_contact_fx,
    "contact visual effects",
)

render = replace_once(
    render,
    '''        contact_angle=0.0\n        if rival.contact_timer>0:\n            contact_angle=rival.contact_side*rival.contact_strength*6.0*math.sin(frame.t*44.0)\n''',
    '''        contact_angle=0.0\n        if rival.contact_timer>0:\n            amp=1.5 if rival.contact_strength<.48 else 4.0 if rival.contact_strength<.82 else 7.0\n            contact_angle=rival.contact_side*rival.contact_strength*amp*math.sin(frame.t*44.0)\n''',
    "rival contact recoil",
)

render = replace_once(
    render,
    '''        if rival.contact_timer>0:\n            _draw_contact_sparks(d,rng,x,y,scale,rival.contact_side,rival.contact_strength)\n''',
    '''        if rival.contact_timer>0:\n            _draw_contact_sparks(d,rng,x,y,scale,rival.contact_side,rival.contact_strength)\n            _draw_tire_scrub(d,rng,x,y,scale,rival.contact_side,rival.contact_strength)\n''',
    "rival tire scrub",
)

render = replace_once(
    render,
    '''    player_contact_angle=0.0\n    if frame.player.contact_timer>0:\n        player_contact_angle=frame.player.contact_side*frame.player.contact_strength*7.0*math.sin(frame.t*42.0)\n''',
    '''    player_contact_angle=0.0\n    if frame.player.contact_timer>0:\n        amp=1.6 if frame.player.contact_strength<.48 else 4.2 if frame.player.contact_strength<.84 else 7.5\n        player_contact_angle=frame.player.contact_side*frame.player.contact_strength*amp*math.sin(frame.t*42.0)\n''',
    "player contact recoil",
)

render = replace_once(
    render,
    '''    if frame.player.contact_timer>0:\n        _draw_contact_sparks(d,rng,px,py,1.15,frame.player.contact_side,frame.player.contact_strength)\n''',
    '''    if frame.player.contact_timer>0:\n        _draw_contact_sparks(d,rng,px,py,1.15,frame.player.contact_side,frame.player.contact_strength)\n        _draw_tire_scrub(d,rng,px,py,1.15,frame.player.contact_side,frame.player.contact_strength)\n''',
    "player tire scrub",
)

RACE.write_text(race)
RENDER.write_text(render)
commit("Make light wheel contact natural and stable")
