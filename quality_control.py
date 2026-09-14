from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QCResult:
    passed: bool
    score: int
    issues: list[str]
    probes: dict

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": self.issues,
            "probes": self.probes,
        }


def _probe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,width,height",
        "-of", "json", str(path),
    ]
    raw = subprocess.check_output(cmd, text=True)
    return json.loads(raw)


def evaluate_episode(video_path: Path, plan: dict, telemetry: dict) -> QCResult:
    issues: list[str] = []
    score = 100
    probe = _probe(video_path)
    streams = probe.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(probe.get("format", {}).get("duration", 0.0) or 0.0)

    if int(video_stream.get("width", 0)) != 1080 or int(video_stream.get("height", 0)) != 1920:
        issues.append("video is not 1080x1920")
        score -= 30
    if not has_audio:
        issues.append("missing audio stream")
        score -= 35
    if not 20.0 <= duration <= 30.0:
        issues.append(f"duration out of range: {duration:.2f}s")
        score -= 20

    if int(telemetry.get("starting_cars", 0)) != 8:
        issues.append("race did not start with exactly 8 cars")
        score -= 30
    if int(telemetry.get("event_count", 0)) < 3:
        issues.append("fewer than 3 meaningful race events")
        score -= 22
    if int(telemetry.get("position_changes", 0)) < 1:
        issues.append("no position change")
        score -= 22
    if int(telemetry.get("featured_visible_frames", 0)) < 30:
        issues.append("featured rival was not visible long enough")
        score -= 18
    if int(telemetry.get("featured_story_beats", 0)) < 2:
        issues.append("featured rival did not participate in enough story beats")
        score -= 18
    if not bool(telemetry.get("has_final_result", False)):
        issues.append("missing final race result")
        score -= 25
    if float(telemetry.get("max_overlap_score", 0.0)) > 0.93:
        issues.append("severe multi-car overlap detected")
        score -= 12

    # Long dead stretches are bad for Shorts even if the render is technically valid.
    if float(telemetry.get("max_event_gap_seconds", 99.0)) > 5.2:
        issues.append("too long without a meaningful beat")
        score -= 15

    passed = score >= 72 and not any(
        x in issues for x in (
            "missing audio stream",
            "video is not 1080x1920",
            "race did not start with exactly 8 cars",
            "missing final race result",
        )
    )
    return QCResult(passed=passed, score=max(0, score), issues=issues, probes={
        "duration": duration,
        "width": int(video_stream.get("width", 0) or 0),
        "height": int(video_stream.get("height", 0) or 0),
        "has_audio": has_audio,
    })


def write_qc(result: QCResult, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)
        f.write("\n")
