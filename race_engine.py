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


class RaceEngine:
    """Arcade race simulation built for short-form story beats.

    A fixed grid starts every race. Cars have persistent relative positions, recurring
    personalities, guaranteed incident windows, actual overtakes, and a proper finish.
    """

    DRIVER_CAST = [
        ("BLUE", "blocker"),
        ("GREEN", "chaos"),
        ("ORANGE", "panic"),
        ("PURPLE", "divebomb"),
        ("WHITE", "rocket"),
        ("CYAN", "showboat"),
        ("LIME", "chaos"),
    ]

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

        # Guaranteed story beats. Randomness chooses WHAT happens, not WHETHER
        # anything happens. This prevents dead 24-second races.
        self.incident_times = [3.4, 7.2, 11.4, 15.6, 19.4]
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
                color=n % 5,
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
        # z < player plane means that car is still ahead, even if it has disappeared
        # beyond the horizon. This keeps the position counter honest.
        return 1 + sum(1 for r in self.rivals if r.z < 1.01)

    def _visible_rivals(self) -> list[RivalState]:
        return [r for r in self.rivals if r.active and 0.15 < r.z < 1.14]

    def _pick_incident_driver(self) -> RivalState | None:
        visible = self._visible_rivals()
        if not visible:
            return None
        # Favor cars near the player so the incident is readable on a phone screen.
        visible.sort(key=lambda r: abs(r.z - 0.88))
        pool = visible[: min(4, len(visible))]
        return self.rng.choice(pool)

    def _start_incident(self, rival: RivalState, i: int) -> str:
        personality = rival.personality
        choices = {
            "blocker": ["block", "brake_check", "swerve"],
            "chaos": ["spin", "swerve", "brake_check"],
            "panic": ["panic", "brake_check", "spin"],
            "divebomb": ["divebomb", "block", "swerve"],
            "rocket": ["divebomb", "showboat", "brake_check"],
            "showboat": ["showboat", "swerve", "spin"],
        }.get(personality, ["swerve", "panic", "spin"])
        behavior = self.rng.choice(choices)
        rival.behavior = behavior

        if behavior == "panic":
            rival.behavior_timer = int(self.fps * 1.05)
            return f"{rival.name} PANICS!"
        if behavior == "brake_check":
            rival.behavior_timer = int(self.fps * 0.95)
            return f"{rival.name} BRAKE CHECK?!"
        if behavior == "swerve":
            rival.behavior_timer = int(self.fps * 1.25)
            rival.target_lane = -0.68 if rival.lane > 0 else 0.68
            return f"{rival.name} WHAT ARE YOU DOING"
        if behavior == "block":
            rival.behavior_timer = int(self.fps * 1.20)
            rival.target_lane = self.player.lane
            return f"{rival.name} WON'T MOVE"
        if behavior == "spin":
            rival.behavior_timer = int(self.fps * 1.15)
            return f"{rival.name} LOST IT!"
        if behavior == "showboat":
            rival.behavior_timer = int(self.fps * 1.40)
            return f"{rival.name} IS SHOWBOATING"

        # Divebomb works best from behind. If this driver is ahead, rapidly close the
        # gap anyway so the move still reads as reckless aggression.
        rival.behavior_timer = int(self.fps * 1.05)
        rival.target_lane = max(-0.68, min(0.68, self.player.lane + self.rng.choice([-0.24, 0.24])))
        return f"{rival.name} DIVEBOMB!"

    def frame(self, i: int) -> RaceFrame:
        t = i / self.fps
        curve = self._curve(t)
        curve_far = self._curve_far(t)
        difficulty = self._difficulty(t)
        event = None
        shake = 0.0

        # Guarantee a visible incident roughly every four seconds.
        if self.incident_cursor < len(self.incident_times) and t >= self.incident_times[self.incident_cursor]:
            driver = self._pick_incident_driver()
            if driver is not None:
                event = self._start_incident(driver, i)
                self.last_event = i
            self.incident_cursor += 1

        # --- Persistent rival simulation ---
        for rival in self.rivals:
            prev_z = rival.z
            rival.rotation *= 0.84

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
                    rival.speed *= 0.963
                    rival.rotation += 0.46
                    rival.target_lane += math.sin(i * 0.32) * 0.028
                elif rival.behavior == "showboat":
                    rival.target_lane = 0.58 * math.sin(i * 0.24)
                    rival.rotation = math.sin(i * 0.20) * 0.13
                    rival.speed += (rival.base_speed * 0.90 - rival.speed) * 0.07
                elif rival.behavior == "divebomb":
                    rival.speed += (min(0.99, rival.base_speed + 0.24) - rival.speed) * 0.17
                    rival.target_lane = max(-0.68, min(0.68, self.player.lane + math.sin(i*.11)*0.18))
            else:
                if rival.behavior != "normal":
                    rival.behavior = "normal"
                rival.speed += (rival.base_speed - rival.speed) * 0.050

            rival.z += (self.player.speed - rival.speed) * 0.017

            if rival.z > 1.30 or rival.z < -0.18:
                rival.active = False

            rival.change_timer -= 1
            if rival.change_timer <= 0 and rival.behavior == "normal":
                rival.target_lane = self.rng.choice([-0.64, -0.32, 0.0, 0.32, 0.64])
                rival.change_timer = self.rng.randint(int(self.fps * 0.8), int(self.fps * 2.3))

            lane_delta = rival.target_lane - rival.lane
            rival.heading = max(-0.18, min(0.18, lane_delta * 0.30))
            rival.lane += lane_delta * (0.022 + 0.020 * min(1.0, rival.speed))
            rival.lane = max(-0.80, min(0.80, rival.lane))

            if rival.active and prev_z < 1.01 <= rival.z and i - self.last_event > self.fps * 0.60:
                event = self.rng.choice(["RED GETS ONE!", "CLEAN PASS!", "AROUND HIM!"])
                self.last_event = i
            elif rival.active and prev_z > 1.01 >= rival.z and rival.speed > self.player.speed and i - self.last_event > self.fps * 0.60:
                event = f"{rival.name} GETS RED!"
                self.last_event = i

        # If two rivals get too close while one is doing something stupid, create an
        # actual chain-reaction spin. This produces the kind of replayable comedy that
        # captions alone cannot.
        active = [r for r in self.rivals if r.active]
        for a_idx in range(len(active)):
            for b_idx in range(a_idx + 1, len(active)):
                a, b = active[a_idx], active[b_idx]
                if abs(a.z - b.z) < 0.045 and abs(a.lane - b.lane) < 0.12:
                    if a.behavior in {"swerve", "spin", "showboat"} or b.behavior in {"swerve", "spin", "showboat"}:
                        a.behavior = b.behavior = "spin"
                        a.behavior_timer = b.behavior_timer = int(self.fps * 0.95)
                        if i - self.last_event > self.fps * 0.65:
                            event = "THEY TOUCHED!"
                            self.last_event = i
                        break

        # --- Player driving AI ---
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

        # Real drift model: the body yaws into the corner while the velocity path
        # continues sliding OUTWARD. The lateral slip then decays as the car recovers.
        drift_trigger = abs(curve) > (0.58 + 0.08 * self.skill) and self.player.speed > 0.47
        self.player.drifting = drift_trigger and not self.player.crashed
        drift_offset = 0.0
        if self.player.drifting:
            sign = math.copysign(1.0, curve)
            intensity = min(1.0, (abs(curve) - 0.54) / 0.44)
            target_slip = -sign * (0.0032 + 0.0042 * intensity)
            self.player.drift_slip += (target_slip - self.player.drift_slip) * 0.18
            self.player.drift_angle += (sign * (0.32 + 0.27 * intensity) - self.player.drift_angle) * 0.15
            drift_offset = -sign * (0.10 + 0.08 * intensity)
            if i - self.last_drift > self.fps * 2.7:
                event = self.rng.choice(["RED SENDS IT SIDEWAYS!", "COUNTERSTEER!", "HOLD THE DRIFT!"])
                self.last_event = i
                self.last_drift = i
        else:
            self.player.drift_slip *= 0.84
            self.player.drift_angle *= 0.82

        target = max(-0.80, min(0.80, base_target + avoid + drift_offset))
        steering_gain = 0.035 + 0.088 * self.skill
        noise = (1.0 - self.skill) * self.rng.uniform(-0.008, 0.008)
        correction = (target - self.player.lane) * steering_gain + noise

        if self.player.crashed:
            self.player.speed *= 0.966
            self.player.heading *= 0.91
            self.player.crash_timer -= 1
            self.player.drifting = False
            self.player.drift_angle *= 0.8
            self.player.drift_slip *= 0.75
            shake = min(0.38, max(0.0, self.player.crash_timer / 85.0))
            if self.player.crash_timer <= 0:
                self.player.crashed = False
                self.player.lane *= 0.65
                self.player.speed = 0.34
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
                shake = 0.34
                self.last_event = i

        road_width = 0.86 - abs(curve) * (0.08 + 0.07 * self.skill)
        road_width = max(0.67, min(0.88, road_width))

        position = self._position()
        progress = min(1.0, t / max(0.1, self.duration))
        if t >= self.duration - 1.35:
            event = f"FINISH: P{position} / 8"

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
        )
