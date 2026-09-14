from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


def _midi(n: int) -> float:
    return 440.0 * (2.0 ** ((n - 69) / 12.0))


def synthesize_audio(
    path: Path,
    speeds: list[float],
    crashes: list[bool],
    impact_strengths: list[float],
    impact_sides: list[float],
    events: list[str | None],
    fps: int,
    sample_rate: int = 22050,
    seed: int = 0,
):
    """Build an original arcade/F1-style soundtrack from race telemetry.

    Everything is synthesized locally with the stdlib: engine, wind, tyres,
    impacts/debris and a fast electronic music bed. Music ducks under big hits
    and commentary beats so the race action stays in front.
    """
    duration = len(speeds) / fps
    total_samples = int(duration * sample_rate)
    rng = random.Random(9917 + len(speeds) + seed)

    phase1 = phase2 = phase3 = 0.0
    bass_phase = arp_phase_l = arp_phase_r = 0.0
    prev_crash = False
    prev_impact = 0.0
    prev_event = None
    impact_start = -999999
    impact_until = -1
    impact_power = 0.0
    impact_side = 0.0

    bpm = 154.0
    beat_hz = bpm / 60.0
    # D-minor-ish loop; deliberately simple and reusable without samples.
    bass_notes = [38, 38, 41, 38, 34, 34, 36, 33]
    arp_notes = [62, 65, 69, 65, 60, 65, 69, 72, 58, 62, 65, 69, 60, 64, 67, 72]

    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for n in range(total_samples):
            t = n / sample_rate
            fi = min(len(speeds) - 1, int(t * fps))
            speed = max(0.0, min(1.0, speeds[fi]))
            crashed = crashes[fi]
            strength = max(0.0, min(1.0, impact_strengths[fi]))
            side = max(-1.0, min(1.0, impact_sides[fi]))
            event = events[fi]

            major_event = bool(event and any(k in event.upper() for k in ('CRASH', 'PILEUP', 'HUGE HIT', 'FULL SPIN', 'BIG CONTACT')))
            new_event_hit = major_event and event != prev_event
            new_impact = strength >= 0.48 and (prev_impact < 0.43 or strength > prev_impact + 0.16)
            if (crashed and not prev_crash) or new_impact or new_event_hit:
                impact_start = n
                impact_power = max(strength, 0.82 if new_event_hit else 0.68)
                impact_side = side
                impact_until = n + int(sample_rate * (0.36 + 0.16 * impact_power))
            prev_crash = crashed
            prev_impact = strength
            prev_event = event

            # Formula-ish engine: layered harmonics whose pitch follows race speed.
            rpm = 115.0 + speed * 420.0
            phase1 += math.tau * rpm / sample_rate
            phase2 += math.tau * rpm * 1.98 / sample_rate
            phase3 += math.tau * rpm * 3.03 / sample_rate
            engine = (
                math.sin(phase1) * 0.42
                + math.sin(phase2) * 0.22
                + math.sin(phase3) * 0.085
            )
            engine *= 0.47 + 0.11 * math.sin(math.tau * (7.0 + speed * 5.0) * t)

            wind_noise = rng.uniform(-1.0, 1.0)
            wind = wind_noise * (0.018 + 0.080 * speed * speed)

            # --- Original fast electronic music bed ---
            beat = t * beat_hz
            beat_frac = beat % 1.0
            half_step = int(beat * 2.0)
            eighth_frac = (beat * 2.0) % 1.0
            sixteenth = int(beat * 4.0)
            sixteenth_frac = (beat * 4.0) % 1.0

            # Kick on each beat, with a short pitch-drop body.
            kick_env = math.exp(-beat_frac * 15.0)
            kick = math.sin(math.tau * (54.0 + 56.0 * math.exp(-beat_frac * 22.0)) * t) * kick_env * 0.25

            # Snare/clap on 2 and 4.
            beat_index = int(beat) % 4
            snare_env = math.exp(-beat_frac * 19.0) if beat_index in (1, 3) else 0.0
            snare = rng.uniform(-1.0, 1.0) * snare_env * 0.10

            # Bright eighth-note hats; noise differentiated by a fast sine gate.
            hat_env = math.exp(-eighth_frac * 28.0)
            hat = rng.uniform(-1.0, 1.0) * hat_env * 0.035

            bass_note = bass_notes[(half_step // 2) % len(bass_notes)]
            bass_freq = _midi(bass_note)
            bass_phase += math.tau * bass_freq / sample_rate
            bass_gate = 0.55 + 0.45 * math.exp(-eighth_frac * 6.0)
            bass = (math.sin(bass_phase) + 0.23 * math.sin(bass_phase * 2.0)) * bass_gate * 0.105

            arp_note = arp_notes[sixteenth % len(arp_notes)]
            arp_freq = _midi(arp_note)
            arp_phase_l += math.tau * arp_freq / sample_rate
            arp_phase_r += math.tau * (arp_freq * 1.003) / sample_rate
            arp_env = math.exp(-sixteenth_frac * 5.0)
            arp_l = math.sin(arp_phase_l) * arp_env * 0.045
            arp_r = math.sin(arp_phase_r + 0.32) * arp_env * 0.045

            pad = (
                math.sin(math.tau * _midi(50) * t) * 0.020
                + math.sin(math.tau * _midi(53) * t + 0.5) * 0.016
                + math.sin(math.tau * _midi(57) * t + 1.0) * 0.014
            )

            # Sidechain the bed around the kick, and duck it hard around impacts.
            sidechain = 0.72 + 0.28 * (1.0 - kick_env)
            impact_env = 0.0
            if n < impact_until:
                age = max(0.0, (n - impact_start) / sample_rate)
                impact_env = max(0.0, 1.0 - age / max(0.001, (impact_until - impact_start) / sample_rate))
            commentary_duck = 0.82 if event else 1.0
            music_gain = sidechain * commentary_duck * (1.0 - 0.72 * impact_env)
            music_l = (kick + snare + hat + bass + arp_l + pad) * music_gain
            music_r = (kick + snare + hat + bass + arp_r + pad) * music_gain

            # --- Impact stack: low thud + carbon crack + debris + tyre scrub ---
            impact_l = impact_r = 0.0
            if n < impact_until:
                age = max(0.0, (n - impact_start) / sample_rate)
                dur = max(0.001, (impact_until - impact_start) / sample_rate)
                env = max(0.0, 1.0 - age / dur)
                thud_freq = max(42.0, 92.0 - age * 120.0)
                thud = math.sin(math.tau * thud_freq * age) * (env ** 2.2) * (0.30 + 0.24 * impact_power)
                crack = rng.uniform(-1.0, 1.0) * (env ** 3.0) * (0.18 + 0.28 * impact_power)
                debris_gate = 1.0 if rng.random() < (0.012 + 0.030 * impact_power) else 0.0
                debris = rng.uniform(-1.0, 1.0) * debris_gate * env * 0.36
                scrub = math.sin(math.tau * (920.0 + 210.0 * math.sin(age * 35.0)) * age) * env * 0.075 * impact_power
                hit = thud + crack + debris + scrub
                pan = 0.32 * impact_side
                impact_l = hit * (1.0 - pan)
                impact_r = hit * (1.0 + pan)

            # Occasional tyre squeal, kept behind music/engine.
            squeal = 0.0
            if speed > 0.58 and math.sin(t * 2.35) > 0.965:
                squeal = math.sin(math.tau * 1450.0 * t) * 0.040

            engine_mix = engine * (0.78 if impact_env > 0.15 else 1.0)
            left_sample = engine_mix + wind + squeal + music_l + impact_l
            right_sample = engine_mix + wind + squeal + music_r + impact_r

            # Small wind stereo spread.
            left_sample += wind_noise * 0.016
            right_sample -= wind_noise * 0.016

            # Soft-ish saturation and clamp.
            left_sample = math.tanh(left_sample * 1.18) * 0.92
            right_sample = math.tanh(right_sample * 1.18) * 0.92
            left = int(max(-1.0, min(1.0, left_sample)) * 32767)
            right = int(max(-1.0, min(1.0, right_sample)) * 32767)
            frames += struct.pack('<hh', left, right)

            if len(frames) >= 65536:
                wf.writeframesraw(frames)
                frames.clear()

        if frames:
            wf.writeframesraw(frames)
