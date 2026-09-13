from __future__ import annotations

from dataclasses import dataclass
import math
import random


@dataclass
class CarState:
    lane: float = 0.0
    speed: float = 0.38
    heading: float = 0.0
    crashed: bool = False
    crash_timer: int = 0


@dataclass
class RaceFrame:
    t: float
    road_curve: float
    road_width: float
    player: CarState
    rivals: list[tuple[float, float, float]]
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
        self.chaos_phase = self.rng.uniform(0, math.tau)

    def _curve(self, t: float) -> float:
        return (
            0.58 * math.sin(t * 0.55 + self.phase)
            + 0.26 * math.sin(t * 1.25 + self.phase * 0.35)
            + 0.12 * math.sin(t * 2.4)
        )

    def _difficulty(self, t: float) -> float:
        ramp = min(1.0, t / max(1.0, self.duration * 0.65))
        return 0.30 + 0.70 * ramp

    def frame(self, i: int) -> RaceFrame:
        t = i / self.fps
        curve = self._curve(t)
        difficulty = self._difficulty(t)
        event = None
        shake = 0.0

        # Low skill reacts late and wanders. Higher skill anticipates corners.
        lookahead = 0.18 + 0.85 * self.skill
        target = self._curve(t + lookahead) * 0.58
        steering_gain = 0.025 + 0.085 * self.skill
        noise = (1.0 - self.skill) * self.rng.uniform(-0.018, 0.018)
        correction = (target - self.player.lane) * steering_gain + noise

        if self.player.crashed:
            self.player.speed *= 0.962
            self.player.heading *= 0.90
            self.player.crash_timer -= 1
            shake = max(0.0, self.player.crash_timer / 18.0)
            if self.player.crash_timer <= 0:
                self.player.crashed = False
                self.player.lane *= 0.70
                self.player.speed = 0.29
                event = "BACK IN IT"
                self.last_event = i
        else:
            self.player.lane += correction
            self.player.heading = max(-0.26, min(0.26, correction * 10.0))
            target_speed = 0.44 + 0.47 * self.skill - abs(curve) * (0.09 + 0.15 * difficulty)
            self.player.speed += (target_speed - self.player.speed) * 0.038

            edge = 0.82 - 0.14 * difficulty
            danger = abs(self.player.lane) > edge
            fail_chance = (1.0 - self.skill) * difficulty * 0.020
            if danger and self.rng.random() < 0.28 + fail_chance:
                self.player.crashed = True
                self.player.crash_timer = self.rng.randint(24, 52)
                self.player.heading += self.rng.choice([-1, 1]) * self.rng.uniform(0.15, 0.32)
                event = self.rng.choice(["TOO WIDE", "BRAKE!", "SPIN!", "NOOO"])
                shake = 1.0
                self.last_event = i

        # Frequent story beats so the Short rarely coasts for long.
        if i - self.last_event > self.fps * 2.6:
            p = self.rng.random()
            if p < 0.010:
                event = self.rng.choice([
                    "BIG SAVE",
                    "LATE BRAKE",
                    "THREE WIDE",
                    "DIVEBOMB",
                    "INSANE LINE",
                    "TRAFFIC CHAOS",
                    "NEAR MISS",
                ])
                self.last_event = i

        # Seven rivals with more dramatic weaving and periodic pack battles.
        rivals: list[tuple[float, float, float]] = []
        for n in range(7):
            pace = 0.62 + n * 0.05 + self.skill * 0.08
            z = (0.06 + n * 0.13 + (t * (0.16 + 0.022 * n + self.skill * 0.03))) % 1.0

            lane = (
                math.sin(t * (0.75 + 0.12 * n) + n * 1.45) * 0.52
                + math.sin(t * (1.9 + 0.07 * n) + n) * 0.12
            )

            # Pack/battle moments bring a few cars close together.
            if int(t * 0.55) % 6 == 3 and n < 3:
                lane = (-0.52 + n * 0.52) + math.sin(t * 3.0 + n) * 0.05
                z = 0.44 + n * 0.07

            lane = max(-0.82, min(0.82, lane))
            rivals.append((z, lane, pace))

        # Near-miss detection gives the chaos a relationship to what is on screen.
        if not self.player.crashed and i - self.last_event > self.fps * 1.4:
            for z, lane, _ in rivals:
                if 0.72 < z < 0.91 and abs(lane - self.player.lane) < 0.15:
                    if self.rng.random() < 0.10:
                        event = self.rng.choice(["NEAR MISS!", "DOOR TO DOOR", "SQUEEZED!", "INCHES!"])
                        shake = max(shake, 0.22)
                        self.last_event = i
                        break

        return RaceFrame(
            t=t,
            road_curve=curve,
            road_width=0.82,
            player=self.player,
            rivals=rivals,
            event_text=event,
            shake=shake,
        )
