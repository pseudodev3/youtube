from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from audio import synthesize_audio
from race_engine import RaceEngine
from renderer import W, H, render_frame

FPS = int(os.getenv("FPS", "30"))
DURATION = float(os.getenv("DURATION", "24"))
OUT = Path("output")
OUT.mkdir(exist_ok=True)


def load_state():
    with open("state.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def ensure_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg was not found in PATH")


def render_video(state):
    ensure_ffmpeg()
    episode = int(state["episode"])
    skill = float(state["driver_skill"])
    seed = episode * 10007 + int(skill * 1000)
    engine = RaceEngine(skill=skill, seed=seed, duration=DURATION, fps=FPS)

    target = OUT / f"episode_{episode:03d}.mp4"
    video_only = OUT / f"episode_{episode:03d}.video.mp4"
    audio_path = OUT / f"episode_{episode:03d}.wav"

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(video_only),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    crashed = False
    speeds: list[float] = []
    crash_flags: list[bool] = []
    impact_strengths: list[float] = []
    impact_sides: list[float] = []
    event_texts: list[str | None] = []

    try:
        for i in range(total):
            rf = engine.frame(i)
            crashed = crashed or rf.player.crashed
            speeds.append(float(rf.player.speed))
            crash_flags.append(bool(rf.player.crashed))

            strongest = 0.0
            strongest_side = 0.0
            if rf.player.contact_timer > 0 and rf.player.contact_strength > strongest:
                strongest = float(rf.player.contact_strength)
                strongest_side = float(rf.player.contact_side)
            for rival in rf.rivals:
                if rival.active and rival.contact_timer > 0 and rival.contact_strength > strongest:
                    strongest = float(rival.contact_strength)
                    strongest_side = float(rival.contact_side)
            if rf.player.crashed and strongest < 0.62:
                strongest = 0.62
                strongest_side = float(rf.player.contact_side)
            impact_strengths.append(strongest)
            impact_sides.append(strongest_side)
            event_texts.append(rf.event_text)

            frame = render_frame(rf, episode=episode, skill=skill, frame_no=i)
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        code = proc.wait()

    if code != 0:
        raise RuntimeError(f"ffmpeg video render failed with exit code {code}")

    # Build engine, original music, tyre and impact audio from the same telemetry.
    synthesize_audio(
        audio_path,
        speeds,
        crash_flags,
        impact_strengths,
        impact_sides,
        event_texts,
        FPS,
        seed=seed,
    )

    mux = [
        "ffmpeg", "-y",
        "-i", str(video_only),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        str(target),
    ]
    subprocess.run(mux, check=True)

    # Keep artifacts tidy; only the final MP4 and metadata need to survive.
    video_only.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)

    return target, crashed


def progress_state(state, crashed):
    skill = float(state["driver_skill"])
    gain = 0.022 if crashed else 0.034
    state["driver_skill"] = round(min(0.98, skill + gain), 3)
    state["episode"] = int(state["episode"]) + 1
    if crashed:
        state["crashes"] = int(state.get("crashes", 0)) + 1
    else:
        state["wins"] = int(state.get("wins", 0)) + 1

    s = state["driver_skill"]
    unlocks = state.setdefault("unlocked_roads", ["training"])
    milestones = [
        (0.28, "country"),
        (0.42, "mountain"),
        (0.56, "night_city"),
        (0.68, "rain"),
        (0.78, "snow"),
        (0.88, "canyon"),
    ]
    for threshold, road in milestones:
        if s >= threshold and road not in unlocks:
            unlocks.append(road)
            state["road_tier"] = int(state.get("road_tier", 1)) + 1

    state["car_tier"] = min(6, 1 + int(s * 6))
    return state


def write_metadata(state_before, target):
    ep = int(state_before["episode"])
    level = max(1, int(float(state_before["driver_skill"]) * 100))
    meta = {
        "title": f"AI Driver Level {level} - Episode {ep} #shorts",
        "description": "An automated racing driver gets better every episode. New roads unlock as its skill increases. #racing #shorts #simulation",
        "video": str(target),
        "episode": ep,
        "level": level,
    }
    with open(OUT / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")


def main():
    state = load_state()
    before = json.loads(json.dumps(state))
    target, crashed = render_video(state)
    write_metadata(before, target)
    progress_state(state, crashed)
    save_state(state)
    print(f"Rendered: {target}")
    print(f"Next episode: {state['episode']} | skill={state['driver_skill']}")


if __name__ == "__main__":
    main()
