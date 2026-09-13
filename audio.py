from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


def synthesize_audio(path: Path, speeds: list[float], crashes: list[bool], fps: int, sample_rate: int = 22050):
    """Generate a lightweight arcade racing soundtrack with only the stdlib.

    The engine pitch follows rendered speed telemetry. Wind grows with speed and
    crash frames get a short noisy impact burst. This keeps Actions self-contained.
    """
    duration = len(speeds) / fps
    total_samples = int(duration * sample_rate)
    rng = random.Random(9917 + len(speeds))

    phase1 = 0.0
    phase2 = 0.0
    phase3 = 0.0
    prev_crash = False
    impact_until = -1

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for n in range(total_samples):
            t = n / sample_rate
            fi = min(len(speeds) - 1, int(t * fps))
            speed = max(0.0, min(1.0, speeds[fi]))
            crashed = crashes[fi]

            if crashed and not prev_crash:
                impact_until = n + int(sample_rate * 0.32)
            prev_crash = crashed

            # Formula-ish engine: several harmonics rather than one clean sine.
            rpm = 115.0 + speed * 420.0
            phase1 += math.tau * rpm / sample_rate
            phase2 += math.tau * rpm * 1.98 / sample_rate
            phase3 += math.tau * rpm * 3.03 / sample_rate
            engine = (
                math.sin(phase1) * 0.44
                + math.sin(phase2) * 0.24
                + math.sin(phase3) * 0.10
            )

            # Gentle pulse gives the synthesized motor some texture.
            engine *= 0.55 + 0.12 * math.sin(math.tau * (7.0 + speed * 5.0) * t)

            # Wind/road hiss rises with speed.
            wind = rng.uniform(-1.0, 1.0) * (0.025 + 0.10 * speed * speed)

            # Short impact/noise burst when a crash begins.
            impact = 0.0
            if n < impact_until:
                remain = (impact_until - n) / (sample_rate * 0.32)
                impact = rng.uniform(-1.0, 1.0) * 0.50 * max(0.0, remain)

            # Occasional tyre-like squeal while the car is moving quickly.
            squeal = 0.0
            if speed > 0.58 and math.sin(t * 2.35) > 0.965:
                squeal = math.sin(math.tau * 1450 * t) * 0.055

            sample = engine + wind + impact + squeal
            sample = max(-0.95, min(0.95, sample))
            val = int(sample * 32767)

            # Tiny stereo spread so headphones do not sound completely mono.
            spread = int(wind * 5000)
            left = max(-32768, min(32767, val + spread))
            right = max(-32768, min(32767, val - spread))
            frames += struct.pack("<hh", left, right)

            if len(frames) >= 65536:
                wf.writeframesraw(frames)
                frames.clear()

        if frames:
            wf.writeframesraw(frames)
