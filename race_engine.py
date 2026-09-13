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

    def _curve(self, t: float) -> float:
        # layered curves create a road that feels authored rather than sinusoidal
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

        # target line anticipates the corner. low skill reacts late and over-corrects.
        lookahead = 0.18 + 0.85 * self.skill
        target = self._curve(t + lookahead) * 0.58
        steering_gain = 0.025 + 0.085 * self.skill
        noise = (1.0 - self.skill) * self.rng.uniform(-0.018, 0.018)
        correction = (target - self.player.lane) * steering_gain + noise

        if self.player.crashed:
            self.player.speed *= 0.965
            self.player.heading *= 0.91
            self.player.crash_timer -= 1
            shake = max(0.0, self.player.crash_timer / 20.0)
            if self.player.crash_timer <= 0:
                self.player.crashed = False
                self.player.lane *= 0.72
                self.player.speed = 0.28
                event = "RECOVERING..."
        else:
            self.player.lane += correction
            self.player.heading = max(-0.22, min(0.22, correction * 9.0))
            target_speed = 0.42 + 0.46 * self.skill - abs(curve) * (0.10 + 0.16 * difficulty)
            self.player.speed += (target_speed - self.player.speed) * 0.035

            edge = 0.82 - 0.14 * difficulty
            danger = abs(self.player.lane) > edge
            fail_chance = (1.0 - self.skill) * difficulty * 0.018
            if danger and self.rng.random() < 0.22 + fail_chance:
                self.player.crashed = True
                self.player.crash_timer = self.rng.randint(20, 42)
                self.player.heading += self.rng.choice([-1, 1]) * self.rng.uniform(0.12, 0.28)
                event = self.rng.choice(["TOO WIDE 💀", "BRAKE!", "NOOO 😭"])
                shake = 1.0

        # scripted-feeling milestones without hardcoding the whole race
        if i - self.last_event > self.fps * 4:
            p = self.rng.random()
            if p < 0.0035:
                event = self.rng.choice(["CLEAN LINE", "NICE SAVE", "GETTING FASTER", "LOCKED IN"])
                self.last_event = i

        rivals: list[tuple[float, float, float]] = []
        for n in range(4):
            z = (0.18 + n * 0.21 + (t * (0.07 + 0.012 * n))) % 1.0
            lane = math.sin(t * (0.42 + 0.08 * n) + n * 1.7) * 0.62
            pace = 0.55 + n * 0.06
            rivals.append((z, lane, pace))

        return RaceFrame(
            t=t,
            road_curve=curve,
            road_width=0.82,
            player=self.player,
            rivals=rivals,
            event_text=event,
            shake=shake,
        )
