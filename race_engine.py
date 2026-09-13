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


@dataclass
class RivalState:
    z: float
    lane: float
    speed: float
    target_lane: float
    heading: float
    color: int
    change_timer: int


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


class RaceEngine:
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
        self.prev_rival_z: list[float] = []

        # Persistent rivals. Some are slower, some faster, so positions can genuinely
        # swap instead of all cars following independent looping animations.
        self.rivals: list[RivalState] = []
        starts = [0.18, 0.31, 0.44, 0.57, 0.69, 0.82, 0.96, 1.08]
        for n, z in enumerate(starts):
            speed_bias = self.rng.uniform(-0.16, 0.17)
            speed = max(0.32, min(0.92, 0.52 + self.skill * 0.22 + speed_bias))
            lane = self.rng.uniform(-0.68, 0.68)
            self.rivals.append(RivalState(
                z=z,
                lane=lane,
                speed=speed,
                target_lane=lane,
                heading=0.0,
                color=n % 5,
                change_timer=self.rng.randint(int(fps * 0.8), int(fps * 2.4)),
            ))
        self.prev_rival_z = [r.z for r in self.rivals]

    def _curve(self, t: float) -> float:
        # Bigger, slower bends with a second harmonic. This produces obvious corners
        # rather than an almost-straight road with only a moving center line.
        return max(-1.0, min(1.0,
            0.82 * math.sin(t * 0.39 + self.phase)
            + 0.34 * math.sin(t * 0.91 + self.phase * 0.31)
        ))

    def _curve_far(self, t: float) -> float:
        return max(-1.0, min(1.0,
            0.70 * math.sin(t * 0.39 + self.phase + 0.75)
            + 0.28 * math.sin(t * 0.82 + 1.6)
        ))

    def _difficulty(self, t: float) -> float:
        ramp = min(1.0, t / max(1.0, self.duration * 0.62))
        return 0.28 + 0.72 * ramp

    def _respawn_ahead(self, rival: RivalState):
        rival.z = self.rng.uniform(0.05, 0.18)
        rival.speed = max(0.32, min(0.94, 0.49 + self.skill * 0.25 + self.rng.uniform(-0.17, 0.15)))
        rival.lane = self.rng.uniform(-0.72, 0.72)
        rival.target_lane = rival.lane
        rival.change_timer = self.rng.randint(int(self.fps * 0.7), int(self.fps * 2.2))

    def _respawn_behind(self, rival: RivalState):
        # Fast car enters from behind and can overtake the player.
        rival.z = self.rng.uniform(1.05, 1.13)
        rival.speed = max(self.player.speed + 0.06, min(0.96, self.player.speed + self.rng.uniform(0.07, 0.20)))
        rival.lane = self.rng.uniform(-0.68, 0.68)
        rival.target_lane = rival.lane
        rival.change_timer = self.rng.randint(int(self.fps * 0.5), int(self.fps * 1.7))

    def frame(self, i: int) -> RaceFrame:
        t = i / self.fps
        curve = self._curve(t)
        curve_far = self._curve_far(t)
        difficulty = self._difficulty(t)
        event = None
        shake = 0.0

        # --- Rival simulation: persistent longitudinal position + lane AI ---
        for n, rival in enumerate(self.rivals):
            prev_z = rival.z

            # Relative longitudinal motion. If player is faster, rival approaches the
            # bottom of screen and gets overtaken. Faster rivals move away toward horizon.
            relative = self.player.speed - rival.speed
            rival.z += relative * 0.016

            rival.change_timer -= 1
            if rival.change_timer <= 0:
                # Pick a new lane. Faster cars are more willing to move around traffic.
                rival.target_lane = self.rng.choice([-0.68, -0.34, 0.0, 0.34, 0.68])
                rival.change_timer = self.rng.randint(int(self.fps * 0.65), int(self.fps * 2.0))

            lane_delta = rival.target_lane - rival.lane
            rival.heading = max(-0.14, min(0.14, lane_delta * 0.25))
            rival.lane += lane_delta * (0.018 + 0.018 * min(1.0, rival.speed))

            # Detect a real pass at the player's plane.
            if prev_z < 1.01 <= rival.z and i - self.last_event > self.fps * 0.8:
                event = self.rng.choice(["GOT ONE!", "OVERTAKE!", "BYE!", "CLEAN PASS"])
                self.last_event = i
            elif prev_z > 1.01 >= rival.z and rival.speed > self.player.speed and i - self.last_event > self.fps * 0.8:
                event = self.rng.choice(["HE'S THROUGH!", "GOT PASSED!", "TOO FAST!", "AROUND THE OUTSIDE!"])
                self.last_event = i

            # Once a car has gone well past either end, bring it back from the opposite
            # side with a new pace. This creates an endless race without teleporting mid-screen.
            if rival.z > 1.18:
                if self.rng.random() < 0.35:
                    self._respawn_behind(rival)
                else:
                    self._respawn_ahead(rival)
            elif rival.z < -0.05:
                if self.rng.random() < 0.62:
                    self._respawn_behind(rival)
                else:
                    self._respawn_ahead(rival)

        # --- Player driving AI ---
        lookahead = 0.35 + 0.85 * self.skill
        base_target = self._curve(t + lookahead) * 0.34

        # If a slower car is directly ahead, deliberately choose an overtaking side.
        avoid = 0.0
        closest = None
        for rival in self.rivals:
            if 0.74 < rival.z < 0.99 and rival.speed < self.player.speed + 0.03:
                gap = abs(rival.lane - self.player.lane)
                if gap < 0.28 and (closest is None or rival.z > closest.z):
                    closest = rival
        if closest is not None:
            pass_side = -1.0 if closest.lane > 0 else 1.0
            avoid = pass_side * (0.28 + 0.18 * self.skill)
            if i - self.last_event > self.fps * 1.1 and self.rng.random() < 0.035:
                event = self.rng.choice(["SETTING UP THE PASS", "DIVEBOMB?", "GO GO GO!"])
                self.last_event = i

        # Real drift sections on sufficiently hard corners. Low/mid skill drifts more,
        # high skill is cleaner but can still slide on the biggest bends.
        drift_trigger = abs(curve) > (0.57 + 0.15 * self.skill) and self.player.speed > 0.49
        drift_window = math.sin(t * 1.9 + self.phase) > -0.20
        self.player.drifting = drift_trigger and drift_window and not self.player.crashed
        drift_offset = 0.0
        if self.player.drifting:
            drift_offset = -math.copysign(0.16 + 0.08 * (1.0 - self.skill), curve)
            if i - self.last_drift > self.fps * 3.0:
                event = self.rng.choice(["DRIFT!", "SIDEWAYS!", "HOLD IT!", "SLIDE JOB!"])
                self.last_event = i
                self.last_drift = i

        target = max(-0.78, min(0.78, base_target + avoid + drift_offset))
        steering_gain = 0.032 + 0.090 * self.skill
        noise = (1.0 - self.skill) * self.rng.uniform(-0.010, 0.010)
        correction = (target - self.player.lane) * steering_gain + noise

        if self.player.crashed:
            self.player.speed *= 0.966
            self.player.heading *= 0.91
            self.player.crash_timer -= 1
            self.player.drifting = False
            shake = min(0.55, max(0.0, self.player.crash_timer / 60.0))
            if self.player.crash_timer <= 0:
                self.player.crashed = False
                self.player.lane *= 0.65
                self.player.speed = 0.34
                event = "BACK IN IT"
                self.last_event = i
        else:
            self.player.lane += correction
            visual_heading = correction * 7.5
            if self.player.drifting:
                visual_heading += math.copysign(0.18, curve)
            self.player.heading = max(-0.28, min(0.28, visual_heading))

            target_speed = 0.50 + 0.42 * self.skill - abs(curve) * (0.07 + 0.11 * difficulty)
            if self.player.drifting:
                target_speed -= 0.035
            self.player.speed += (target_speed - self.player.speed) * 0.035

            edge = 0.86 - 0.11 * difficulty
            danger = abs(self.player.lane) > edge
            fail_chance = (1.0 - self.skill) * difficulty * 0.012
            if danger and self.rng.random() < 0.14 + fail_chance:
                self.player.crashed = True
                self.player.crash_timer = self.rng.randint(20, 38)
                self.player.heading += self.rng.choice([-1, 1]) * self.rng.uniform(0.12, 0.22)
                event = self.rng.choice(["TOO WIDE", "SPIN!", "NO GRIP!", "OH NO!"])
                shake = 0.55
                self.last_event = i

        # Occasional race-story moments, but these are secondary to actual passes/drifts.
        if i - self.last_event > self.fps * 3.2 and self.rng.random() < 0.006:
            event = self.rng.choice(["THREE WIDE", "HUNTING THEM DOWN", "BATTLE ON!", "FULL SEND"])
            self.last_event = i

        return RaceFrame(
            t=t,
            road_curve=curve,
            road_curve_far=curve_far,
            road_width=0.82,
            player=self.player,
            rivals=self.rivals,
            event_text=event,
            shake=shake,
        )
