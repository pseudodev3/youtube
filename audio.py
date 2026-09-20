from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


def _midi(n: int) -> float:
    return 440.0 * (2.0 ** ((n - 69) / 12.0))


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


TRACK_TEXTURES = {
    "training":       {"bass": 1.00, "arp": 1.00, "pad": 0.90, "drums": 1.00},
    "country":        {"bass": 0.92, "arp": 0.88, "pad": 1.08, "drums": 0.92},
    "mountain":       {"bass": 0.92, "arp": 0.82, "pad": 1.18, "drums": 0.94},
    "night_city":     {"bass": 1.10, "arp": 1.14, "pad": 0.92, "drums": 1.05},
    "rain":           {"bass": 0.98, "arp": 0.78, "pad": 1.14, "drums": 0.90},
    "coast":          {"bass": 0.88, "arp": 0.96, "pad": 1.20, "drums": 0.88},
    "snow":           {"bass": 0.82, "arp": 0.72, "pad": 1.34, "drums": 0.76},
    "canyon":         {"bass": 1.08, "arp": 0.78, "pad": 0.82, "drums": 1.10},
    "desert":         {"bass": 1.00, "arp": 0.74, "pad": 1.04, "drums": 0.96},
    "forest":         {"bass": 0.88, "arp": 0.72, "pad": 1.22, "drums": 0.82},
    "street":         {"bass": 1.12, "arp": 1.02, "pad": 0.84, "drums": 1.10},
    "tunnel":         {"bass": 1.16, "arp": 0.86, "pad": 0.70, "drums": 1.08},
    "neon_rain":      {"bass": 1.10, "arp": 1.25, "pad": 1.02, "drums": 1.04},
    "alpine":         {"bass": 0.82, "arp": 0.70, "pad": 1.42, "drums": 0.78},
    "extreme_canyon": {"bass": 1.14, "arp": 0.72, "pad": 0.74, "drums": 1.14},
}

STORY_TEXTURES = {
    "clean_duel":      {"bass": 1.00, "arp": 1.08, "pad": 1.00, "drums": 1.00},
    "rival_blockade":  {"bass": 1.07, "arp": 0.96, "pad": 0.94, "drums": 1.05},
    "revenge":         {"bass": 1.08, "arp": 1.02, "pad": 0.92, "drums": 1.06},
    "pileup_escape":   {"bass": 1.04, "arp": 0.92, "pad": 0.88, "drums": 1.12},
    "comeback":        {"bass": 0.98, "arp": 1.00, "pad": 1.10, "drums": 1.03},
    "chaos_race":      {"bass": 1.06, "arp": 0.96, "pad": 0.84, "drums": 1.15},
    "showdown":        {"bass": 1.08, "arp": 1.10, "pad": 1.04, "drums": 1.10},
}


def synthesize_audio(
    path: Path,
    speeds: list[float],
    crashes: list[bool],
    impact_strengths: list[float],
    impact_sides: list[float],
    events: list[str | None],
    music_states: list[str],
    fps: int,
    sample_rate: int = 22050,
    seed: int = 0,
    drift_slips: list[float] | None = None,
    drift_angles: list[float] | None = None,
    longitudinal_loads: list[float] | None = None,
    track_key: str = "training",
    story_type: str = "",
):
    """Build adaptive race audio from telemetry without affecting simulation.

    Engine load, pseudo gear changes, tyres, wind, ambience and impacts are all
    driven by already-rendered race telemetry. Track/story profiles only change
    sound texture; they never feed back into race physics or showrunner timing.
    """
    duration = len(speeds) / fps
    total_samples = int(duration * sample_rate)
    rng = random.Random(9917 + len(speeds) + seed)

    drift_slips = drift_slips or [0.0] * len(speeds)
    drift_angles = drift_angles or [0.0] * len(speeds)
    longitudinal_loads = longitudinal_loads or [0.0] * len(speeds)

    track_texture = TRACK_TEXTURES.get(track_key, TRACK_TEXTURES["training"])
    story_texture = STORY_TEXTURES.get(
        story_type,
        {"bass": 1.0, "arp": 1.0, "pad": 1.0, "drums": 1.0},
    )
    texture = {
        key: track_texture[key] * story_texture[key]
        for key in ("bass", "arp", "pad", "drums")
    }

    # Oscillators.
    phase1 = phase2 = phase3 = phase4 = 0.0
    tyre_phase = 0.0
    bass_phase = arp_phase_l = arp_phase_r = 0.0
    ambience_phase = 0.0
    ambience_phase2 = 0.0

    # Stateful telemetry-derived audio controls.
    prev_crash = False
    prev_impact = 0.0
    prev_event = None
    impact_start = -999999
    impact_until = -1
    impact_power = 0.0
    impact_side = 0.0

    current_gear = 1
    last_shift = -999999
    shift_start = -999999
    up_thresholds = [0.18, 0.32, 0.47, 0.63, 0.79]
    down_thresholds = [0.00, 0.12, 0.25, 0.39, 0.54, 0.69]

    wind_lp_common = 0.0
    wind_lp_side = 0.0
    ambience_lp_l = 0.0
    ambience_lp_r = 0.0

    # Small delay line for tunnel/city reflections. It only affects the mix.
    delay_samples = max(1, int(sample_rate * 0.105))
    echo_l = [0.0] * delay_samples
    echo_r = [0.0] * delay_samples
    echo_idx = 0

    bpm = 154.0
    beat_hz = bpm / 60.0
    bass_notes = [38, 38, 41, 38, 34, 34, 36, 33]
    arp_notes = [62, 65, 69, 65, 60, 65, 69, 72, 58, 62, 65, 69, 60, 64, 67, 72]
    energies = {
        "calm": 0.42,
        "build": 0.68,
        "battle": 1.00,
        "danger": 0.84,
        "recovery": 0.50,
        "finale": 1.10,
    }

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for n in range(total_samples):
            t = n / sample_rate
            fi = min(len(speeds) - 1, int(t * fps))
            speed = _clamp(speeds[fi])
            crashed = crashes[fi]
            strength = _clamp(impact_strengths[fi])
            side = max(-1.0, min(1.0, impact_sides[fi]))
            event = events[fi]
            state = music_states[fi] if fi < len(music_states) else "battle"
            energy = energies.get(state, 0.75)
            drift_slip = abs(drift_slips[min(fi, len(drift_slips) - 1)])
            drift_angle = abs(drift_angles[min(fi, len(drift_angles) - 1)])
            longitudinal = max(
                -1.0,
                min(1.0, longitudinal_loads[min(fi, len(longitudinal_loads) - 1)]),
            )

            major_event = bool(event and any(k in event.upper() for k in (
                "CRASH", "PILEUP", "HUGE HIT", "FULL SPIN", "BIG CONTACT"
            )))
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

            # --- Engine V2 -------------------------------------------------
            # Gear state follows speed with hysteresis. It is presentation only.
            shift_gap = n - last_shift
            if current_gear < 6 and speed > up_thresholds[current_gear - 1] and shift_gap > int(sample_rate * 0.24):
                current_gear += 1
                last_shift = shift_start = n
            elif (
                current_gear > 1
                and speed < down_thresholds[current_gear - 1]
                and shift_gap > int(sample_rate * 0.34)
            ):
                current_gear -= 1
                last_shift = shift_start = n

            gear_low = 0.0 if current_gear == 1 else down_thresholds[current_gear - 1]
            gear_high = 1.0 if current_gear == 6 else up_thresholds[current_gear - 1]
            rev_span = max(0.08, gear_high - gear_low)
            rev = _clamp((speed - gear_low) / rev_span)

            throttle = _clamp(0.42 + 0.42 * max(0.0, longitudinal) + 0.18 * speed - 0.28 * max(0.0, -longitudinal))
            decel = _clamp(max(0.0, -longitudinal))
            shift_age = (n - shift_start) / sample_rate
            shift_drop = 1.0
            if 0.0 <= shift_age < 0.22:
                shift_drop = 1.0 - 0.24 * math.exp(-shift_age * 15.0)

            engine_hz = (128.0 + 330.0 * rev + 54.0 * speed) * shift_drop
            phase1 += math.tau * engine_hz / sample_rate
            phase2 += math.tau * engine_hz * 1.98 / sample_rate
            phase3 += math.tau * engine_hz * 3.03 / sample_rate
            phase4 += math.tau * engine_hz * 4.07 / sample_rate

            harmonic_bite = 0.055 + 0.065 * throttle + 0.025 * rev
            engine = (
                math.sin(phase1) * 0.40
                + math.sin(phase2) * (0.18 + 0.07 * throttle)
                + math.sin(phase3) * (0.060 + 0.045 * throttle)
                + math.sin(phase4) * harmonic_bite
            )
            pulse = 0.45 + 0.07 * math.sin(math.tau * (7.2 + speed * 5.3) * t)
            engine *= pulse * (0.84 + 0.20 * throttle)
            if decel > 0.08:
                # Coarser, quieter lift-off tone.
                engine *= 1.0 - 0.16 * decel
                engine += math.sin(phase2 * 0.51) * 0.018 * decel

            # Small deterministic lift-off crackle. No random event scheduling.
            crackle = 0.0
            crackle_phase = (t * 31.0 + seed * 0.013) % 1.0
            if speed > 0.54 and decel > 0.30 and crackle_phase < 0.035:
                crackle = rng.uniform(-1.0, 1.0) * (0.020 + 0.028 * decel)

            # --- Air + actual tyre telemetry -------------------------------
            common_noise = rng.uniform(-1.0, 1.0)
            side_noise = rng.uniform(-1.0, 1.0)
            wind_lp_common = wind_lp_common * 0.91 + common_noise * 0.09
            wind_lp_side = wind_lp_side * 0.88 + side_noise * 0.12
            wind_base = 0.010 + 0.064 * speed * speed
            if track_key == "snow":
                wind_base *= 0.68
            elif track_key in {"coast", "alpine", "desert", "extreme_canyon"}:
                wind_base *= 1.16
            stereo_width = 0.18 + 0.72 * speed
            wind_l = wind_lp_common * wind_base + wind_lp_side * wind_base * stereo_width
            wind_r = wind_lp_common * wind_base - wind_lp_side * wind_base * stereo_width

            slip_norm = _clamp(drift_slip / 0.0088)
            angle_norm = _clamp(drift_angle / 0.52)
            contact_scrub = _clamp(strength * 0.72)
            tyre_load = max(slip_norm, angle_norm * 0.82, contact_scrub * 0.52)
            tyre_hz = 1020.0 + 520.0 * tyre_load + 180.0 * speed
            tyre_phase += math.tau * tyre_hz / sample_rate
            tyre_noise = rng.uniform(-1.0, 1.0)
            tyre = (
                math.sin(tyre_phase) * 0.048
                + tyre_noise * 0.030
            ) * (tyre_load ** 1.35)
            if crashed:
                tyre += math.sin(tyre_phase * 0.72) * 0.025

            # --- World ambience --------------------------------------------
            ambience_lp_l = ambience_lp_l * 0.94 + rng.uniform(-1.0, 1.0) * 0.06
            ambience_lp_r = ambience_lp_r * 0.94 + rng.uniform(-1.0, 1.0) * 0.06
            ambience_phase += math.tau * 57.0 / sample_rate
            ambience_phase2 += math.tau * 113.0 / sample_rate
            ambience_l = ambience_r = 0.0

            if track_key in {"rain", "neon_rain"}:
                rain_hiss_l = rng.uniform(-1.0, 1.0) * (0.030 if track_key == "rain" else 0.025)
                rain_hiss_r = rng.uniform(-1.0, 1.0) * (0.030 if track_key == "rain" else 0.025)
                ambience_l += rain_hiss_l + ambience_lp_l * 0.012
                ambience_r += rain_hiss_r + ambience_lp_r * 0.012
                if track_key == "neon_rain":
                    neon_hum = math.sin(ambience_phase * 1.31) * 0.010
                    ambience_l += neon_hum
                    ambience_r += neon_hum
            elif track_key == "tunnel":
                hum = math.sin(ambience_phase) * 0.020 + math.sin(ambience_phase2) * 0.009
                ambience_l += hum + ambience_lp_l * 0.008
                ambience_r += hum + ambience_lp_r * 0.008
            elif track_key in {"night_city", "street"}:
                hum = math.sin(ambience_phase * 1.17) * 0.010
                ambience_l += hum + ambience_lp_l * 0.010
                ambience_r += hum + ambience_lp_r * 0.010
            elif track_key == "coast":
                swell = math.sin(math.tau * 0.22 * t) * 0.008
                ambience_l += ambience_lp_l * 0.020 + swell
                ambience_r += ambience_lp_r * 0.020 + swell
            elif track_key in {"desert", "canyon", "extreme_canyon"}:
                gain = 0.018 if track_key == "canyon" else 0.024
                ambience_l += ambience_lp_l * gain
                ambience_r += ambience_lp_r * gain
            elif track_key in {"mountain", "alpine"}:
                ambience_l += ambience_lp_l * 0.014
                ambience_r += ambience_lp_r * 0.014
            elif track_key == "forest":
                rustle = 0.55 + 0.45 * math.sin(t * 1.7)
                ambience_l += ambience_lp_l * 0.015 * rustle
                ambience_r += ambience_lp_r * 0.015 * rustle
            elif track_key == "snow":
                ambience_l += ambience_lp_l * 0.006
                ambience_r += ambience_lp_r * 0.006
            elif track_key == "country":
                ambience_l += ambience_lp_l * 0.009
                ambience_r += ambience_lp_r * 0.009

            # --- Original adaptive music, now textured by map/story --------
            beat = t * beat_hz
            beat_frac = beat % 1.0
            half_step = int(beat * 2.0)
            eighth_frac = (beat * 2.0) % 1.0
            sixteenth = int(beat * 4.0)
            sixteenth_frac = (beat * 4.0) % 1.0

            kick_env = math.exp(-beat_frac * 15.0)
            kick_density = 0.50 if state == "calm" else 0.70 if state == "recovery" else 1.0
            kick = (
                math.sin(math.tau * (54.0 + 56.0 * math.exp(-beat_frac * 22.0)) * t)
                * kick_env * 0.25 * kick_density * texture["drums"]
            )

            beat_index = int(beat) % 4
            snare_on = beat_index in (1, 3) and state not in {"calm", "recovery"}
            snare_env = math.exp(-beat_frac * 19.0) if snare_on else 0.0
            snare = rng.uniform(-1.0, 1.0) * snare_env * 0.10 * texture["drums"]

            hat_density = 0.28 if state == "calm" else 0.42 if state == "recovery" else 1.0
            hat_env = math.exp(-eighth_frac * 28.0)
            hat = rng.uniform(-1.0, 1.0) * hat_env * 0.035 * hat_density * texture["drums"]

            bass_note = bass_notes[(half_step // 2) % len(bass_notes)]
            bass_freq = _midi(bass_note)
            bass_phase += math.tau * bass_freq / sample_rate
            bass_gate = 0.55 + 0.45 * math.exp(-eighth_frac * 6.0)
            bass = (
                math.sin(bass_phase) + 0.23 * math.sin(bass_phase * 2.0)
            ) * bass_gate * 0.105 * texture["bass"]

            arp_note = arp_notes[sixteenth % len(arp_notes)]
            arp_freq = _midi(arp_note)
            arp_phase_l += math.tau * arp_freq / sample_rate
            arp_phase_r += math.tau * (arp_freq * 1.003) / sample_rate
            arp_env = math.exp(-sixteenth_frac * 5.0)
            arp_density = 0.20 if state == "calm" else 0.35 if state == "recovery" else 0.72 if state == "build" else 1.0
            arp_l = math.sin(arp_phase_l) * arp_env * 0.045 * arp_density * texture["arp"]
            arp_r = math.sin(arp_phase_r + 0.32) * arp_env * 0.045 * arp_density * texture["arp"]

            pad = (
                math.sin(math.tau * _midi(50) * t) * 0.020
                + math.sin(math.tau * _midi(53) * t + 0.5) * 0.016
                + math.sin(math.tau * _midi(57) * t + 1.0) * 0.014
            ) * texture["pad"]

            if state == "danger":
                pad *= 0.45
                bass *= 1.12
            elif state == "finale":
                bass *= 1.12
                arp_l *= 1.10
                arp_r *= 1.10

            sidechain = 0.72 + 0.28 * (1.0 - kick_env)
            impact_env = 0.0
            if n < impact_until:
                age = max(0.0, (n - impact_start) / sample_rate)
                impact_env = max(
                    0.0,
                    1.0 - age / max(0.001, (impact_until - impact_start) / sample_rate),
                )

            commentary_duck = 0.78 if event else 1.0
            impact_music_duck = max(0.16, 1.0 - 0.78 * impact_env)
            music_gain = 1.12 * energy * sidechain * commentary_duck * impact_music_duck
            music_l = (kick + snare + hat + bass + arp_l + pad) * music_gain
            music_r = (kick + snare + hat + bass + arp_r + pad) * music_gain

            # --- Impact stack ----------------------------------------------
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
                scrub = (
                    math.sin(math.tau * (920.0 + 210.0 * math.sin(age * 35.0)) * age)
                    * env * 0.075 * impact_power
                )
                hit = thud + crack + debris + scrub
                pan = 0.32 * impact_side
                impact_l = hit * (1.0 - pan)
                impact_r = hit * (1.0 + pan)

            engine_mix = (engine + crackle) * max(0.56, 1.0 - 0.38 * impact_env)
            ambience_duck = max(0.55, 1.0 - 0.42 * impact_env)
            ambience_l *= ambience_duck
            ambience_r *= ambience_duck

            dry_l = engine_mix + wind_l + tyre + ambience_l + impact_l
            dry_r = engine_mix + wind_r + tyre + ambience_r + impact_r

            # Tunnel gets a real short slap; city worlds get only a trace.
            reflection = 0.18 if track_key == "tunnel" else 0.055 if track_key in {"night_city", "street", "neon_rain"} else 0.0
            delayed_l = echo_l[echo_idx]
            delayed_r = echo_r[echo_idx]
            echo_l[echo_idx] = dry_l * 0.82
            echo_r[echo_idx] = dry_r * 0.82
            echo_idx = (echo_idx + 1) % delay_samples

            left_sample = dry_l + music_l + delayed_l * reflection
            right_sample = dry_r + music_r + delayed_r * reflection

            # Headroom for phone speakers + AAC intersample peaks.
            left_sample = math.tanh(left_sample * 1.16) * 0.75
            right_sample = math.tanh(right_sample * 1.16) * 0.75
            left = int(max(-1.0, min(1.0, left_sample)) * 32767)
            right = int(max(-1.0, min(1.0, right_sample)) * 32767)
            frames += struct.pack("<hh", left, right)

            if len(frames) >= 65536:
                wf.writeframesraw(frames)
                frames.clear()

        if frames:
            wf.writeframesraw(frames)
