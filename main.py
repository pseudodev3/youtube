from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
from pathlib import Path

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
        str(target),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    crashed = False
    try:
        for i in range(total):
            rf = engine.frame(i)
            crashed = crashed or rf.player.crashed
            frame = render_frame(rf, episode=episode, skill=skill, frame_no=i)
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {code}")

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
