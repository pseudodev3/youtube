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
    behavior: str = "normal"
    behavior_timer: int = 0
    gag_cooldown: int = 0
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


class RaceEngine:
    """Small arcade race simulation used to author a Short.

    The field is fixed at the start of the race. Nobody teleports in halfway through.
    Cars keep persistent relative positions so overtakes are real crossings of the
    player's plane, while occasional driver personalities create funny moments.
    """

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

        # Fixed seven-car field. Six start ahead and one starts just behind so the
        # opening can already contain both attacking and defending situations.
        self.rivals: list[RivalState] = []
        starts = [0.20, 0.34, 0.49, 0.64, 0.78, 0.91, 1.09]
        for n, z in enumerate(starts):
            # Wide pace spread is intentional: it creates genuine catching and passing.
            bias = self.rng.uniform(-0.15, 0.16)
            base_speed = max(0.34, min(0.91, 0.50 + self.skill * 0.23 + bias))
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
                gag_cooldown=self.rng.randint(int(fps * 2.0), int(fps * 6.0)),
            ))

    @staticmethod
    def _ease01(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return x * x * (3.0 - 2.0 * x)

    def _curve(self, t: float) -> float:
        """Authored corner sequence rather than one endless gentle sine wave.

        Training-road lore remains: early drivers get wider, slower versions of real
        corners. As skill rises, the same timeline becomes tighter and more technical.
        """
        section_len = 3.4
        section = int(t // section_len) % 7
        u = (t % section_len) / section_len
        arch = math.sin(math.pi * u)

        if section == 0:      # opening sweeper
            shape = 0.42 * arch
        elif section == 1:    # obvious S bend
            shape = 0.72 * math.sin(math.tau * u) * arch
        elif section == 2:    # long left hairpin
            shape = -0.94 * (arch ** 1.25)
        elif section == 3:    # late-apex right hander
            late = self._ease01((u - 0.30) / 0.70)
            shape = 0.92 * late * math.sin(math.pi * late)
        elif section == 4:    # quick chicane
            shape = 0.76 * math.sin(3.0 * math.pi * u) * arch
        elif section == 5:    # right hairpin
            shape = 0.98 * (arch ** 1.18)
        else:                 # exit sweeper
            shape = -0.58 * arch

        # Beginners still get corners; later skill simply tightens the course.
        challenge = 0.74 + 0.34 * self.skill
        texture = 0.10 * math.sin(t * 0.82 + self.phase)
        return max(-1.0, min(1.0, shape * challenge + texture))

    def _curve_far(self, t: float) -> float:
        # Look further down the road so the renderer can show upcoming bends/chicanes.
        return self._curve(t + 1.05)

    def _difficulty(self, t: float) -> float:
        ramp = min(1.0, t / max(1.0, self.duration * 0.62))
        return 0.30 + 0.70 * ramp

    def _start_funny_behavior(self, rival: RivalState, i: int) -> str | None:
        """Give one driver a short, visible personality mistake/stunt."""
        if rival.behavior != "normal" or not (0.12 < rival.z < 1.14):
            return None

        choices = ["panic", "swerve", "block", "spin"]
        # A car behind the player can also try a ridiculous divebomb.
        if rival.z > 0.96:
            choices.append("divebomb")
        behavior = self.rng.choice(choices)
        rival.behavior = behavior

        if behavior == "panic":
            rival.behavior_timer = self.rng.randint(int(self.fps * 0.65), int(self.fps * 1.05))
            return self.rng.choice(["PANIC BRAKE!", "WHY DID HE BRAKE?", "BRO??"])
        if behavior == "swerve":
            rival.behavior_timer = self.rng.randint(int(self.fps * 0.8), int(self.fps * 1.35))
            rival.target_lane = -0.62 if rival.lane > 0 else 0.62
            return self.rng.choice(["WHAT IS HE DOING?", "RANDOM SWERVE!", "PICK A LANE!"])
        if behavior == "block":
            rival.behavior_timer = self.rng.randint(int(self.fps * 0.8), int(self.fps * 1.3))
            rival.target_lane = max(-0.68, min(0.68, self.player.lane))
            return self.rng.choice(["HE'S BLOCKING!", "NO WAY THROUGH", "MOVE!"])
        if behavior == "spin":
            rival.behavior_timer = self.rng.randint(int(self.fps * 0.65), int(self.fps * 1.1))
            return self.rng.choice(["HE SPUN!", "NOT LIKE THAT!", "LOST IT!"])

        rival.behavior_timer = self.rng.randint(int(self.fps * 0.55), int(self.fps * 0.95))
        rival.target_lane = max(-0.66, min(0.66, self.player.lane + self.rng.choice([-0.22, 0.22])))
        return self.rng.choice(["DIVEBOMB!", "FROM NOWHERE!", "SEND IT!"])

    def frame(self, i: int) -> RaceFrame:
        t = i / self.fps
        curve = self._curve(t)
        curve_far = self._curve_far(t)
        difficulty = self._difficulty(t)
        event = None
        shake = 0.0

        # --- Persistent rival simulation ---
        for rival in self.rivals:
            prev_z = rival.z
            rival.rotation *= 0.86
            rival.gag_cooldown -= 1

            if rival.behavior_timer > 0:
                rival.behavior_timer -= 1
                if rival.behavior == "panic":
                    rival.speed += (rival.base_speed * 0.52 - rival.speed) * 0.16
                    rival.heading = math.sin(i * 0.28) * 0.04
                elif rival.behavior == "swerve":
                    rival.speed += (rival.base_speed * 0.94 - rival.speed) * 0.08
                elif rival.behavior == "block":
                    rival.target_lane = max(-0.68, min(0.68, self.player.lane))
                    rival.speed += (rival.base_speed * 0.91 - rival.speed) * 0.07
                elif rival.behavior == "spin":
                    rival.speed *= 0.972
                    rival.rotation += 0.38
                    rival.target_lane += math.sin(i * 0.35) * 0.018
                elif rival.behavior == "divebomb":
                    rival.speed += (min(0.98, rival.base_speed + 0.18) - rival.speed) * 0.13
            else:
                if rival.behavior != "normal":
                    rival.behavior = "normal"
                    rival.gag_cooldown = self.rng.randint(int(self.fps * 3.5), int(self.fps * 7.5))
                rival.speed += (rival.base_speed - rival.speed) * 0.045

            # Relative longitudinal movement: this is what makes passes real.
            rival.z += (self.player.speed - rival.speed) * 0.016

            # Cars that have genuinely left the race view stay gone. No mid-race spawning.
            if rival.z > 1.28 or rival.z < -0.16:
                rival.active = False

            rival.change_timer -= 1
            if rival.change_timer <= 0 and rival.behavior == "normal":
                rival.target_lane = self.rng.choice([-0.64, -0.32, 0.0, 0.32, 0.64])
                rival.change_timer = self.rng.randint(int(self.fps * 0.75), int(self.fps * 2.2))

            lane_delta = rival.target_lane - rival.lane
            rival.heading = max(-0.16, min(0.16, lane_delta * 0.28))
            rival.lane += lane_delta * (0.020 + 0.020 * min(1.0, rival.speed))
            rival.lane = max(-0.78, min(0.78, rival.lane))

            # Trigger actual funny/crazy behavior rather than just captioning nothing.
            if rival.active and rival.gag_cooldown <= 0 and i - self.last_event > self.fps * 0.9:
                if self.rng.random() < 0.018:
                    funny = self._start_funny_behavior(rival, i)
                    if funny:
                        event = funny
                        self.last_event = i

            # Real player/rival passes at the player's plane.
            if rival.active and prev_z < 1.01 <= rival.z and i - self.last_event > self.fps * 0.75:
                event = self.rng.choice(["GOT ONE!", "OVERTAKE!", "BYE!", "CLEAN PASS"])
                self.last_event = i
            elif rival.active and prev_z > 1.01 >= rival.z and rival.speed > self.player.speed and i - self.last_event > self.fps * 0.75:
                event = self.rng.choice(["HE'S THROUGH!", "GOT PASSED!", "AROUND THE OUTSIDE!"])
                self.last_event = i

        # --- Player driving AI ---
        lookahead = 0.36 + 0.82 * self.skill
        base_target = self._curve(t + lookahead) * 0.35

        # Find traffic ahead and choose a passing side instead of following it forever.
        avoid = 0.0
        closest = None
        for rival in self.rivals:
            if not rival.active:
                continue
            if 0.72 < rival.z < 1.00 and rival.speed < self.player.speed + 0.035:
                gap = abs(rival.lane - self.player.lane)
                if gap < 0.30 and (closest is None or rival.z > closest.z):
                    closest = rival
        if closest is not None:
            pass_side = -1.0 if closest.lane > 0 else 1.0
            avoid = pass_side * (0.30 + 0.16 * self.skill)
            if i - self.last_event > self.fps * 1.2 and self.rng.random() < 0.025:
                event = self.rng.choice(["SETTING UP THE PASS", "GO GO GO!", "AROUND HIM!"])
                self.last_event = i

        # Sustained drift on strong corners. The renderer rotates the whole car, so this
        # needs a real angle rather than just a slightly bent nose.
        drift_trigger = abs(curve) > (0.46 + 0.11 * self.skill) and self.player.speed > 0.46
        self.player.drifting = drift_trigger and not self.player.crashed
        drift_offset = 0.0
        if self.player.drifting:
            sign = math.copysign(1.0, curve)
            intensity = min(1.0, (abs(curve) - 0.44) / 0.50)
            self.player.drift_angle = sign * (0.42 + 0.22 * intensity)
            drift_offset = -sign * (0.17 + 0.09 * intensity)
            if i - self.last_drift > self.fps * 2.5:
                event = self.rng.choice(["DRIFT!", "SIDEWAYS!", "HOLD IT!", "SLIDE JOB!"])
                self.last_event = i
                self.last_drift = i
        else:
            self.player.drift_angle *= 0.82

        target = max(-0.80, min(0.80, base_target + avoid + drift_offset))
        steering_gain = 0.034 + 0.088 * self.skill
        noise = (1.0 - self.skill) * self.rng.uniform(-0.009, 0.009)
        correction = (target - self.player.lane) * steering_gain + noise

        if self.player.crashed:
            self.player.speed *= 0.966
            self.player.heading *= 0.91
            self.player.crash_timer -= 1
            self.player.drifting = False
            self.player.drift_angle *= 0.8
            shake = min(0.45, max(0.0, self.player.crash_timer / 70.0))
            if self.player.crash_timer <= 0:
                self.player.crashed = False
                self.player.lane *= 0.65
                self.player.speed = 0.34
                event = "BACK IN IT"
                self.last_event = i
        else:
            self.player.lane += correction
            visual_heading = correction * 7.0
            self.player.heading = max(-0.22, min(0.22, visual_heading))

            target_speed = 0.52 + 0.40 * self.skill - abs(curve) * (0.075 + 0.12 * difficulty)
            if self.player.drifting:
                target_speed -= 0.045
            self.player.speed += (target_speed - self.player.speed) * 0.036

            edge = 0.84 - 0.12 * difficulty
            danger = abs(self.player.lane) > edge
            fail_chance = (1.0 - self.skill) * difficulty * 0.012
            if danger and self.rng.random() < 0.14 + fail_chance:
                self.player.crashed = True
                self.player.crash_timer = self.rng.randint(20, 38)
                self.player.heading += self.rng.choice([-1, 1]) * self.rng.uniform(0.10, 0.20)
                event = self.rng.choice(["TOO WIDE", "SPIN!", "NO GRIP!", "OH NO!"])
                shake = 0.45
                self.last_event = i

        # Course width tightens on big bends, increasingly so as the driver levels up.
        road_width = 0.86 - abs(curve) * (0.07 + 0.07 * self.skill)
        road_width = max(0.68, min(0.88, road_width))

        return RaceFrame(
            t=t,
            road_curve=curve,
            road_curve_far=curve_far,
            road_width=road_width,
            player=self.player,
            rivals=self.rivals,
            event_text=event,
            shake=shake,
        )
