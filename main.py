from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from audio import synthesize_audio
from career import apply_uploaded_episode, load_career, save_career
from metadata import build_metadata, write_metadata
from quality_control import evaluate_episode, write_qc
from race_engine import RaceEngine
from renderer import W, H, render_frame
from showrunner import music_state_at, plan_episode, write_plan
from youtube_upload import upload_enabled, upload_video

FPS = int(os.getenv("FPS", "30"))
DURATION = float(os.getenv("DURATION", "24"))
MAX_RENDER_ATTEMPTS = int(os.getenv("MAX_RENDER_ATTEMPTS", "3"))
OUT = Path("output")
OUT.mkdir(exist_ok=True)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def ensure_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg/ffprobe were not found in PATH")


def _overlap_score(frame) -> float:
    """Cheap telemetry-only overlap score used by QC, not by the physics itself."""
    cars = [("RED", 1.01, float(frame.player.lane))]
    cars += [
        (r.name, float(r.z), float(r.lane))
        for r in frame.rivals if r.active
    ]
    best = 0.0
    for i in range(len(cars)):
        for j in range(i + 1, len(cars)):
            _, za, la = cars[i]
            _, zb, lb = cars[j]
            z_overlap = max(0.0, 1.0 - abs(za - zb) / 0.060)
            lane_overlap = max(0.0, 1.0 - abs(la - lb) / 0.155)
            best = max(best, z_overlap * lane_overlap)
    return best


def render_video(career: dict, plan: dict) -> tuple[Path, dict]:
    ensure_ffmpeg()
    episode = int(plan["episode"])
    skill = float(career["driver_skill"])
    seed = int(plan["seed"])
    engine = RaceEngine(skill=skill, seed=seed, duration=DURATION, fps=FPS, plan=plan)

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
    speeds: list[float] = []
    crash_flags: list[bool] = []
    impact_strengths: list[float] = []
    impact_sides: list[float] = []
    event_texts: list[str | None] = []
    music_states: list[str] = []

    starting_cars = 0
    positions: list[int] = []
    event_frames: list[int] = []
    event_log: list[dict] = []
    seen_story_captions: set[str] = set()
    featured_visible_frames = 0
    featured_contact_events = 0
    player_ever_crashed = False
    max_overlap = 0.0
    previous_event: str | None = None
    previous_featured_contact = False
    last_frame = None

    featured_name = str(plan["featured_rival"])
    planned_captions = {
        str(b.get("caption")): b for b in plan.get("beats", []) if b.get("caption")
    }

    try:
        for i in range(total):
            rf = engine.frame(i)
            last_frame = rf
            if i == 0:
                starting_cars = int(rf.total_cars)

            player_ever_crashed = player_ever_crashed or bool(rf.player.crashed)
            speeds.append(float(rf.player.speed))
            crash_flags.append(bool(rf.player.crashed))
            positions.append(int(rf.position))

            strongest = 0.0
            strongest_side = 0.0
            if rf.player.contact_timer > 0 and rf.player.contact_strength > strongest:
                strongest = float(rf.player.contact_strength)
                strongest_side = float(rf.player.contact_side)

            featured = None
            for rival in rf.rivals:
                if rival.name == featured_name:
                    featured = rival
                if rival.active and rival.contact_timer > 0 and rival.contact_strength > strongest:
                    strongest = float(rival.contact_strength)
                    strongest_side = float(rival.contact_side)

            if rf.player.crashed and strongest < 0.62:
                strongest = 0.62
                strongest_side = float(rf.player.contact_side)
            impact_strengths.append(strongest)
            impact_sides.append(strongest_side)
            event_texts.append(rf.event_text)
            music_states.append(music_state_at(plan, rf.t))

            if featured and featured.active and 0.0 < featured.z < 1.18:
                featured_visible_frames += 1
            featured_contact = bool(
                featured
                and featured.active
                and rf.player.contact_timer > 0
                and featured.contact_timer > 0
                and abs(featured.z - 1.01) < 0.11
            )
            if featured_contact and not previous_featured_contact:
                featured_contact_events += 1
            previous_featured_contact = featured_contact

            if rf.event_text and rf.event_text != previous_event:
                event_frames.append(i)
                event_log.append({"frame": i, "time": round(rf.t, 3), "text": rf.event_text})
                if rf.event_text in planned_captions:
                    seen_story_captions.add(rf.event_text)
            previous_event = rf.event_text
            max_overlap = max(max_overlap, _overlap_score(rf))

            frame = render_frame(rf, episode=episode, skill=skill, frame_no=i)
            if not proc.stdin:
                raise RuntimeError("ffmpeg stdin closed unexpectedly")
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        code = proc.wait()

    if code != 0:
        raise RuntimeError(f"ffmpeg video render failed with exit code {code}")
    if last_frame is None:
        raise RuntimeError("race engine produced zero frames")

    synthesize_audio(
        audio_path,
        speeds,
        crash_flags,
        impact_strengths,
        impact_sides,
        event_texts,
        music_states,
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
    video_only.unlink(missing_ok=True)
    audio_path.unlink(missing_ok=True)

    gaps = []
    points = [0] + event_frames + [total - 1]
    for a, b in zip(points, points[1:]):
        gaps.append(max(0.0, (b - a) / FPS))

    position_changes = sum(1 for a, b in zip(positions, positions[1:]) if a != b)
    featured_story_beats = sum(
        1 for caption in seen_story_captions
        if planned_captions.get(caption, {}).get("actor") == "featured"
    )
    final_event_texts = [x["text"] for x in event_log if x["time"] >= DURATION - 2.0]
    has_final_result = any(
        ("TARGET CLEARED" in text or "MISSED BY" in text)
        for text in final_event_texts
    )

    telemetry = {
        "episode": episode,
        "attempt": int(plan.get("attempt", 0)),
        "starting_cars": starting_cars,
        "final_position": int(last_frame.position),
        "target_position": int(plan["target_position"]),
        "position_changes": position_changes,
        "event_count": len(event_frames),
        "events": event_log,
        "featured_rival": featured_name,
        "featured_visible_frames": featured_visible_frames,
        "featured_story_beats": featured_story_beats,
        "featured_contact_events": featured_contact_events,
        "player_crashed": player_ever_crashed,
        "max_overlap_score": round(max_overlap, 4),
        "max_event_gap_seconds": round(max(gaps or [DURATION]), 3),
        "has_final_result": has_final_result,
        "music_states_used": sorted(set(music_states)),
    }
    return target, telemetry


def _write_status(**payload) -> None:
    _write_json(OUT / "run_status.json", payload)


def main() -> None:
    career = load_career()

    # Scheduled runs stay dormant until the user adds YouTube credentials. Manual
    # workflow/run-now triggers still render complete preview artifacts for tuning.
    if os.getenv("GITHUB_EVENT_NAME") == "schedule" and not upload_enabled():
        _write_status(status="skipped", reason="youtube_secrets_not_configured")
        print("Scheduled run skipped: YouTube upload secrets are not configured yet.")
        return

    chosen = None
    for attempt in range(max(1, MAX_RENDER_ATTEMPTS)):
        plan_obj = plan_episode(career, attempt=attempt, duration=DURATION)
        plan = plan_obj.to_dict()
        write_plan(plan_obj)
        target, telemetry = render_video(career, plan)
        _write_json(OUT / f"telemetry_attempt_{attempt}.json", telemetry)

        qc = evaluate_episode(target, plan, telemetry)
        write_qc(qc, OUT / f"qc_attempt_{attempt}.json")
        print(f"QC attempt {attempt + 1}/{MAX_RENDER_ATTEMPTS}: score={qc.score} issues={qc.issues}")
        if qc.passed:
            chosen = (plan, target, telemetry, qc)
            break

    if chosen is None:
        _write_status(status="qc_failed", episode=int(career["episode"]))
        raise RuntimeError(f"Episode {career['episode']} failed QC after {MAX_RENDER_ATTEMPTS} attempts")

    plan, target, telemetry, qc = chosen
    _write_json(OUT / "telemetry.json", telemetry)
    write_qc(qc, OUT / "qc.json")
    metadata = build_metadata(plan, telemetry, target)
    write_metadata(metadata, OUT / "metadata.json")

    if upload_enabled():
        video_id = upload_video(target, metadata)
        advanced = apply_uploaded_episode(career, plan, telemetry, video_id)
        save_career(advanced)
        _write_status(
            status="uploaded",
            episode=int(plan["episode"]),
            video_id=video_id,
            qc_score=qc.score,
            next_episode=int(advanced["episode"]),
        )
        print(f"Uploaded episode {plan['episode']}: https://youtu.be/{video_id}")
        print(f"Career advanced to episode {advanced['episode']}")
    else:
        _write_status(
            status="preview",
            episode=int(plan["episode"]),
            qc_score=qc.score,
            note="career_not_advanced_until_youtube_upload_succeeds",
        )
        print(f"Preview rendered: {target}")
        print("YouTube upload disabled; career state intentionally NOT advanced.")


if __name__ == "__main__":
    main()
