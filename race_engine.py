from __future__ import annotations

from dataclasses import dataclass
import math
import random


@dataclass
class CarState:
    lane: float = 0.0
    speed: float = 0.46
    heading: float = 0.0
    crashed: bool = False
    crash_timer: int = 0
    drifting: bool = False
    drift_angle: float = 0.0
    drift_slip: float = 0.0
    contact_timer: int = 0
    contact_side: float = 0.0
    contact_strength: float = 0.0
    crash_rotation: float = 0.0
    crash_spin_rate: float = 0.0
    crash_slide_velocity: float = 0.0


@dataclass
class RivalState:
    z: float
    lane: float
    speed: float
    base_speed: float
    target_lane: float
    heading: float
    rotation: float
    color: int
    change_timer: int
    name: str
    personality: str
    behavior: str = "normal"
    behavior_timer: int = 0
    active: bool = True
    contact_timer: int = 0
    contact_side: float = 0.0
    contact_strength: float = 0.0
    spin_rate: float = 0.0
    slide_velocity: float = 0.0


@dataclass
class RaceFrame:
    t: float
    road_curve: float
    road_curve_far: float
    road_width: float
    player: CarState
    rivals: list[RivalState]
    event_text: str | None
    shake: float
    position: int
    total_cars: int
    race_progress: float
    target_position: int
    featured_rival: str
    objective_text: str


class RaceEngine:
    """Arcade F1-cartoon race simulation built around recurring characters and drama."""

    DRIVER_CAST = [
        ("BLUE", "blocker"),
        ("GREEN", "chaos"),
        ("ORANGE", "panic"),
        ("PURPLE", "divebomb"),
        ("WHITE", "rocket"),
        ("CYAN", "showboat"),
        ("LIME", "chaos"),
    ]

    PERSONALITY_LINES = {
        "blocker": "never gives Red room",
        "chaos": "causes something stupid every race",
        "panic": "brakes at the worst possible time",
        "divebomb": "thinks every gap belongs to him",
        "rocket": "is annoyingly fast",
        "showboat": "would rather look cool than win",
    }

    def __init__(self, skill: float, seed: int, duration: float = 24.0, fps: int = 30):
        self.skill = max(0.02, min(0.98, skill))
        self.seed = seed
        self.duration = duration
        self.fps = fps
        self.rng = random.Random(seed)
        self.player = CarState()
        self.phase = self.rng.uniform(0, math.tau)
        self.last_event = -999
        self.last_drift = -999

        self.target_position = 5 if self.skill < .34 else 4 if self.skill < .58 else 3
        self.featured_index = seed % len(self.DRIVER_CAST)
        self.featured_rival = self.DRIVER_CAST[self.featured_index][0]
        featured_personality = self.DRIVER_CAST[self.featured_index][1]
        self.objective_text = (
            f"TARGET P{self.target_position} • {self.featured_rival} "
            f"{self.PERSONALITY_LINES[featured_personality]}"
        )

        self.incident_times = [3.1, 6.6, 10.2, 14.0, 17.7, 20.7]
        self.incident_cursor = 0

        self.rivals: list[RivalState] = []
        starts = [0.20, 0.34, 0.49, 0.64, 0.78, 0.91, 1.09]
        for n, z in enumerate(starts):
            name, personality = self.DRIVER_CAST[n]
            bias = self.rng.uniform(-0.15, 0.16)
            base_speed = max(0.34, min(0.91, 0.50 + self.skill * 0.23 + bias))
            if personality == "rocket":
                base_speed = min(0.94, base_speed + 0.08)
            elif personality == "panic":
                base_speed = max(0.36, base_speed - 0.04)
            if n == len(starts) - 1:
                base_speed = max(base_speed, 0.60 + self.skill * 0.20)
            lane = self.rng.choice([-0.58, -0.28, 0.0, 0.28, 0.58])
            self.rivals.append(RivalState(
                z=z,
                lane=lane,
                speed=base_speed,
                base_speed=base_speed,
                target_lane=lane,
                heading=0.0,
                rotation=0.0,
                color=n,
                change_timer=self.rng.randint(int(fps * 0.8), int(fps * 2.3)),
                name=name,
                personality=personality,
            ))

    @staticmethod
    def _ease01(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return x * x * (3.0 - 2.0 * x)

    def _curve(self, t: float) -> float:
        section_len = 3.25
        section = int(t // section_len) % 7
        u = (t % section_len) / section_len
        arch = math.sin(math.pi * u)
        if section == 0:
            shape = 0.48 * arch
        elif section == 1:
            shape = 0.80 * math.sin(math.tau * u) * arch
        elif section == 2:
            shape = -1.00 * (arch ** 1.22)
        elif section == 3:
            late = self._ease01((u - 0.24) / 0.76)
            shape = 0.98 * late * math.sin(math.pi * late)
        elif section == 4:
            shape = 0.86 * math.sin(3.0 * math.pi * u) * arch
        elif section == 5:
            shape = 1.00 * (arch ** 1.14)
        else:
            shape = -0.66 * arch
        challenge = 0.78 + 0.30 * self.skill
        texture = 0.08 * math.sin(t * 0.82 + self.phase)
        return max(-1.0, min(1.0, shape * challenge + texture))

    def _curve_far(self, t: float) -> float:
        return self._curve(t + 1.10)

    def _difficulty(self, t: float) -> float:
        ramp = min(1.0, t / max(1.0, self.duration * 0.62))
        return 0.30 + 0.70 * ramp

    def _position(self) -> int:
        return 1 + sum(1 for r in self.rivals if r.z < 1.01)

    def _visible_rivals(self) -> list[RivalState]:
        return [r for r in self.rivals if r.active and 0.12 < r.z < 1.15]

    def _pick_incident_driver(self) -> RivalState | None:
        visible = self._visible_rivals()
        if not visible:
            return None
        featured = next((r for r in visible if r.name == self.featured_rival), None)
        if featured and self.rng.random() < 0.62:
            return featured
        visible.sort(key=lambda r: abs(r.z - 0.88))
        return self.rng.choice(visible[: min(4, len(visible))])

    def _kick_spin(self, rival: RivalState, direction: float | None = None,
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

    def _start_incident(self, rival: RivalState, i: int) -> str:
        choices = {
            "blocker": ["block", "brake_check", "swerve"],
            "chaos": ["spin", "swerve", "brake_check"],
            "panic": ["panic", "brake_check", "spin"],
            "divebomb": ["divebomb", "block", "swerve"],
            "rocket": ["divebomb", "showboat", "brake_check"],
            "showboat": ["showboat", "swerve", "spin"],
        }.get(rival.personality, ["swerve", "panic", "spin"])
        behavior = self.rng.choice(choices)

        if behavior == "spin":
            self._kick_spin(rival, severity=0.70)
            return f"{rival.name} THREW IT AWAY 💀"

        rival.behavior = behavior
        if behavior == "panic":
            rival.behavior_timer = int(self.fps * 1.05)
            return f"{rival.name} PANICS 😂"
        if behavior == "brake_check":
            rival.behavior_timer = int(self.fps * 0.95)
            return f"{rival.name} BRAKE CHECKS RED?!"
        if behavior == "swerve":
            rival.behavior_timer = int(self.fps * 1.25)
            rival.target_lane = -0.68 if rival.lane > 0 else 0.68
            return f"{rival.name} PICK A LANE 😭"
        if behavior == "block":
            rival.behavior_timer = int(self.fps * 1.20)
            rival.target_lane = self.player.lane
            return f"{rival.name} IS PARKING THE BUS"
        if behavior == "showboat":
            rival.behavior_timer = int(self.fps * 1.40)
            return f"{rival.name} SHOWBOATS MID-RACE 😭"

        rival.behavior_timer = int(self.fps * 1.05)
        rival.target_lane = max(-0.68, min(0.68, self.player.lane + self.rng.choice([-0.24, 0.24])))
        return f"{rival.name} DIVEBOMBS FROM NARNIA"

    @staticmethod
    def _contact_side(a_lane: float, b_lane: float, fallback: float = 1.0) -> float:
        if abs(a_lane - b_lane) < 1e-4:
            return fallback
        return 1.0 if b_lane > a_lane else -1.0

    def _resolve_rival_contacts(self, i: int) -> str | None:
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

    def _resolve_player_contacts(self, i: int) -> str | None:
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

    def frame(self, i: int) -> RaceFrame:
        t = i / self.fps
        curve = self._curve(t)
        curve_far = self._curve_far(t)
        difficulty = self._difficulty(t)
        event = None
        shake = 0.0

        if self.player.contact_timer > 0:
            self.player.contact_timer -= 1
        else:
            self.player.contact_strength *= 0.80

        if self.incident_cursor < len(self.incident_times) and t >= self.incident_times[self.incident_cursor]:
            driver = self._pick_incident_driver()
            if driver is not None:
                event = self._start_incident(driver, i)
                self.last_event = i
            self.incident_cursor += 1

        for rival in self.rivals:
            prev_z = rival.z
            if rival.contact_timer > 0:
                rival.contact_timer -= 1
            else:
                rival.contact_strength *= 0.80

            if rival.behavior_timer > 0:
                rival.behavior_timer -= 1
                if rival.behavior == "panic":
                    rival.speed += (rival.base_speed * 0.48 - rival.speed) * 0.18
                    rival.heading = math.sin(i * 0.32) * 0.06
                elif rival.behavior == "brake_check":
                    rival.speed += (rival.base_speed * 0.34 - rival.speed) * 0.24
                    rival.target_lane = max(-0.72, min(0.72, self.player.lane + math.sin(i*.18)*0.12))
                elif rival.behavior == "swerve":
                    rival.target_lane = 0.70 * math.sin(i * 0.18)
                    rival.speed += (rival.base_speed * 0.91 - rival.speed) * 0.08
                elif rival.behavior == "block":
                    rival.target_lane = max(-0.68, min(0.68, self.player.lane))
                    rival.speed += (rival.base_speed * 0.88 - rival.speed) * 0.08
                elif rival.behavior == "spin":
                    spin_target_speed = max(0.09, rival.base_speed * 0.18)
                    rival.speed += (spin_target_speed - rival.speed) * 0.17
                    rival.lane += rival.slide_velocity
                    rival.slide_velocity *= 0.945
                    if rival.behavior_timer > int(self.fps * 0.42):
                        rival.rotation += rival.spin_rate
                        rival.spin_rate *= 0.965
                        if abs(rival.rotation) >= 1.05:
                            rival.rotation = math.copysign(1.05, rival.rotation)
                            rival.spin_rate *= 0.30
                    else:
                        rival.spin_rate *= 0.68
                        rival.rotation *= 0.80
                        rival.slide_velocity *= 0.82
                    rival.target_lane = rival.lane
                    rival.heading *= 0.75
                elif rival.behavior == "big_spin":
                    # Full crash spin. The nose can pass through 180/360 degrees, but
                    # the car is nearly stopped and sliding while that happens.
                    spin_target_speed = max(0.055, rival.base_speed * 0.10)
                    rival.speed += (spin_target_speed - rival.speed) * 0.20
                    rival.lane += rival.slide_velocity
                    rival.slide_velocity *= 0.952
                    if rival.behavior_timer > int(self.fps * 0.38):
                        rival.rotation += rival.spin_rate
                        rival.spin_rate *= 0.991
                    else:
                        turn = 360.0 / 70.0
                        rival.rotation = ((rival.rotation + turn / 2) % turn) - turn / 2
                        rival.rotation *= 0.74
                        rival.spin_rate *= 0.60
                        rival.slide_velocity *= 0.78
                    rival.target_lane = rival.lane
                    rival.heading *= 0.62
                elif rival.behavior == "recover":
                    rival.rotation *= 0.72
                    rival.spin_rate *= 0.55
                    rival.slide_velocity *= 0.72
                    recovery_speed = max(0.18, rival.base_speed * 0.45)
                    rival.speed += (recovery_speed - rival.speed) * 0.10
                    rival.target_lane = rival.lane
                    rival.heading *= 0.70
                elif rival.behavior == "showboat":
                    rival.target_lane = 0.58 * math.sin(i * 0.24)
                    rival.rotation = math.sin(i * 0.20) * 0.13
                    rival.speed += (rival.base_speed * 0.90 - rival.speed) * 0.07
                elif rival.behavior == "divebomb":
                    rival.speed += (min(0.99, rival.base_speed + 0.24) - rival.speed) * 0.17
                    rival.target_lane = max(-0.68, min(0.68, self.player.lane + math.sin(i*.11)*0.18))
            else:
                if rival.behavior in {"spin", "big_spin"}:
                    turn = 360.0 / 70.0
                    rival.rotation = ((rival.rotation + turn / 2) % turn) - turn / 2
                    rival.behavior = "recover"
                    rival.behavior_timer = int(self.fps * 0.55)
                    rival.spin_rate *= 0.40
                    rival.slide_velocity *= 0.50
                elif rival.behavior == "recover":
                    rival.behavior = "normal"
                    rival.rotation = 0.0
                    rival.spin_rate = 0.0
                    rival.slide_velocity = 0.0
                    rival.speed = max(rival.speed, rival.base_speed * 0.42)
                else:
                    if rival.behavior != "normal":
                        rival.behavior = "normal"
                    rival.rotation *= 0.72
                    if abs(rival.rotation) < 0.01:
                        rival.rotation = 0.0
                    rival.speed += (rival.base_speed - rival.speed) * 0.050

            rival.z += (self.player.speed - rival.speed) * 0.017
            if rival.z > 1.30 or rival.z < -0.18:
                rival.active = False

            rival.change_timer -= 1
            if rival.change_timer <= 0 and rival.behavior == "normal":
                rival.target_lane = self.rng.choice([-0.64, -0.32, 0.0, 0.32, 0.64])
                rival.change_timer = self.rng.randint(int(self.fps * 0.8), int(self.fps * 2.3))

            if rival.behavior not in {"spin", "big_spin", "recover"}:
                lane_delta = rival.target_lane - rival.lane
                rival.heading = max(-0.18, min(0.18, lane_delta * 0.30))
                rival.lane += lane_delta * (0.022 + 0.020 * min(1.0, rival.speed))
            rival.lane = max(-0.80, min(0.80, rival.lane))

            if rival.active and prev_z < 1.01 <= rival.z and i - self.last_event > self.fps * 0.60:
                event = self.rng.choice(["RED GETS ONE!", "RED SNEAKS THROUGH!", "CLEAN PASS!"])
                self.last_event = i
            elif rival.active and prev_z > 1.01 >= rival.z and rival.speed > self.player.speed and i - self.last_event > self.fps * 0.60:
                event = f"{rival.name} GETS RED!"
                self.last_event = i

        if t > self.duration - 5.0:
            survivors = [
                r for r in self.rivals
                if r.active and r.behavior not in {"spin", "big_spin", "recover"}
            ]
            survivors.sort(key=lambda r: abs(r.z - 1.0))
            for rival in survivors[:3]:
                desired = 0.91 if rival.z < 1.0 else 1.07
                rival.z += (desired - rival.z) * 0.008
                rival.speed += (self.player.speed + self.rng.uniform(-0.035, 0.035) - rival.speed) * 0.035

        rival_contact_event = self._resolve_rival_contacts(i)
        if rival_contact_event:
            event = rival_contact_event
            shake = max(shake, 0.12)

        lookahead = 0.38 + 0.80 * self.skill
        base_target = self._curve(t + lookahead) * 0.35
        avoid = 0.0
        closest = None
        for rival in self.rivals:
            if not rival.active:
                continue
            if 0.70 < rival.z < 1.00 and rival.speed < self.player.speed + 0.05:
                gap = abs(rival.lane - self.player.lane)
                if gap < 0.32 and (closest is None or rival.z > closest.z):
                    closest = rival
        if closest is not None:
            pass_side = -1.0 if closest.lane > 0 else 1.0
            avoid = pass_side * (0.30 + 0.17 * self.skill)

        drift_trigger = abs(curve) > (0.58 + 0.08 * self.skill) and self.player.speed > 0.47
        self.player.drifting = drift_trigger and not self.player.crashed
        drift_offset = 0.0
        if self.player.drifting:
            sign = math.copysign(1.0, curve)
            intensity = min(1.0, (abs(curve) - 0.54) / 0.44)
            target_slip = -sign * (0.0038 + 0.0050 * intensity)
            self.player.drift_slip += (target_slip - self.player.drift_slip) * 0.20
            target_angle = sign * (0.28 + 0.24 * intensity)
            self.player.drift_angle += (target_angle - self.player.drift_angle) * 0.17
            drift_offset = -sign * (0.10 + 0.08 * intensity)
            if i - self.last_drift > self.fps * 2.7:
                event = self.rng.choice(["RED CATCHES THE SLIDE!", "COUNTERSTEER!", "HE SAVED IT!"])
                self.last_event = i
                self.last_drift = i
        else:
            self.player.drift_slip *= 0.82
            self.player.drift_angle *= 0.80

        target = max(-0.80, min(0.80, base_target + avoid + drift_offset))
        steering_gain = 0.035 + 0.088 * self.skill
        noise = (1.0 - self.skill) * self.rng.uniform(-0.008, 0.008)
        correction = (target - self.player.lane) * steering_gain + noise

        if self.player.crashed:
            self.player.crash_timer -= 1
            self.player.drifting = False
            self.player.drift_angle *= 0.8
            self.player.drift_slip *= 0.75
            if abs(self.player.crash_spin_rate) > 0.002:
                crash_target_speed = 0.07
                self.player.speed += (crash_target_speed - self.player.speed) * 0.18
                self.player.lane += self.player.crash_slide_velocity
                self.player.crash_slide_velocity *= 0.95
                if self.player.crash_timer > int(self.fps * 0.34):
                    self.player.crash_rotation += self.player.crash_spin_rate
                    self.player.crash_spin_rate *= 0.991
                else:
                    turn = 360.0 / 70.0
                    self.player.crash_rotation = (
                        (self.player.crash_rotation + turn / 2) % turn
                    ) - turn / 2
                    self.player.crash_rotation *= 0.72
                    self.player.crash_spin_rate *= 0.58
                    self.player.crash_slide_velocity *= 0.76
            else:
                self.player.speed *= 0.966
                self.player.heading *= 0.91
            self.player.lane = max(-0.82, min(0.82, self.player.lane))
            shake = max(shake, min(0.38, max(0.0, self.player.crash_timer / 85.0)))
            if self.player.crash_timer <= 0:
                self.player.crashed = False
                self.player.lane *= 0.65
                self.player.speed = max(0.30, self.player.speed)
                self.player.crash_rotation = 0.0
                self.player.crash_spin_rate = 0.0
                self.player.crash_slide_velocity = 0.0
                event = "RED'S BACK!"
                self.last_event = i
        else:
            self.player.lane += correction + self.player.drift_slip
            self.player.heading = max(-0.22, min(0.22, correction * 6.5))
            target_speed = 0.52 + 0.40 * self.skill - abs(curve) * (0.075 + 0.12 * difficulty)
            if self.player.drifting:
                target_speed -= 0.055
            self.player.speed += (target_speed - self.player.speed) * 0.036
            edge = 0.84 - 0.12 * difficulty
            danger = abs(self.player.lane) > edge
            fail_chance = (1.0 - self.skill) * difficulty * 0.010
            if danger and self.rng.random() < 0.12 + fail_chance:
                self.player.crashed = True
                self.player.crash_timer = self.rng.randint(18, 34)
                self.player.heading += self.rng.choice([-1, 1]) * self.rng.uniform(0.10, 0.18)
                event = self.rng.choice(["RED THREW IT AWAY!", "TOO MUCH!", "NO GRIP!"])
                shake = max(shake, 0.34)
                self.last_event = i

        player_contact_event = self._resolve_player_contacts(i)
        if player_contact_event:
            event = player_contact_event
            shake = max(shake, 0.16 + self.player.contact_strength * 0.12)

        road_width = 0.86 - abs(curve) * (0.08 + 0.07 * self.skill)
        road_width = max(0.67, min(0.88, road_width))
        position = self._position()
        progress = min(1.0, t / max(0.1, self.duration))

        if t >= self.duration - 1.30:
            if position <= self.target_position:
                event = f"TARGET CLEARED! P{position} 🔥"
            else:
                missed = position - self.target_position
                event = f"MISSED BY {missed} PLACE" if missed == 1 else f"MISSED BY {missed} PLACES"

        return RaceFrame(
            t=t,
            road_curve=curve,
            road_curve_far=curve_far,
            road_width=road_width,
            player=self.player,
            rivals=self.rivals,
            event_text=event,
            shake=shake,
            position=position,
            total_cars=8,
            race_progress=progress,
            target_position=self.target_position,
            featured_rival=self.featured_rival,
            objective_text=self.objective_text,
        )
