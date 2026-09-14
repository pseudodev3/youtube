from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path

from story_beats import build_story, choose_story_type
from track_system import choose_track

PLAN_PATH = Path("output/episode_plan.json")


@dataclass
class EpisodePlan:
    episode: int
    attempt: int
    seed: int
    featured_rival: str
    target_position: int
    story_type: str
    story_label: str
    hook: str
    objective_text: str
    track: dict
    beats: list[dict]
    music_arc: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _stable_seed(episode: int, attempt: int, skill: float) -> int:
    raw = f"gridloop:{episode}:{attempt}:{skill:.3f}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:12], 16) % 2_000_000_000


def _choose_featured_rival(career: dict, rng: random.Random) -> str:
    episode = int(career.get("episode", 1))
    last = career.get("last_featured_rival")
    scored: list[tuple[float, str]] = []
    for name, data in career.get("rivals", {}).items():
        rivalry = int(data.get("rivalry", 1))
        last_featured = int(data.get("last_featured_episode", -999))
        cooldown = max(0, 3 - (episode - last_featured))
        score = rivalry * 2.4 + rng.random() * 4.0 - cooldown * 4.5
        if name == last:
            score -= 2.2
        scored.append((score, name))
    scored.sort(reverse=True)
    pool = [name for _, name in scored[:3]] or ["BLUE"]
    return rng.choice(pool)


def _target_position(skill: float, career: dict, rng: random.Random) -> int:
    if skill < 0.34:
        base = 5
    elif skill < 0.58:
        base = 4
    elif skill < 0.82:
        base = 3
    else:
        base = 2
    if career.get("last_result") == "target_missed" and rng.random() < 0.55:
        base = min(5, base + 1)
    return base


def _music_arc(story_type: str, track: dict) -> list[dict]:
    finale = 18.0
    if story_type in {"pileup_escape", "chaos_race"}:
        return [
            {"time": 0.0, "state": "calm"},
            {"time": 3.0, "state": "build"},
            {"time": 7.0, "state": "battle"},
            {"time": 10.0, "state": "danger"},
            {"time": 14.5, "state": "recovery"},
            {"time": finale, "state": "finale"},
        ]
    return [
        {"time": 0.0, "state": "calm"},
        {"time": 4.0, "state": "build"},
        {"time": 8.0, "state": "battle"},
        {"time": 13.0, "state": "recovery"},
        {"time": finale, "state": "finale"},
    ]


def plan_episode(career: dict, attempt: int = 0, duration: float = 24.0) -> EpisodePlan:
    episode = int(career.get("episode", 1))
    skill = float(career.get("driver_skill", 0.2))
    seed = _stable_seed(episode, attempt, skill)
    rng = random.Random(seed)

    featured = _choose_featured_rival(career, rng)
    target = _target_position(skill, career, rng)
    story_type = choose_story_type(rng, career, featured)
    story = build_story(story_type, featured, rng, duration=duration)
    track = choose_track(career, rng)

    objective = f"TARGET P{target} • BEAT {featured} • {track['variant'].upper()}"
    return EpisodePlan(
        episode=episode,
        attempt=attempt,
        seed=seed,
        featured_rival=featured,
        target_position=target,
        story_type=story_type,
        story_label=story["label"],
        hook=story["hook"],
        objective_text=objective,
        track=track,
        beats=story["beats"],
        music_arc=_music_arc(story_type, track),
    )


def write_plan(plan: EpisodePlan, path: Path = PLAN_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(plan.to_dict(), f, indent=2)
        f.write("\n")


def music_state_at(plan: dict, t: float) -> str:
    state = "calm"
    for marker in plan.get("music_arc", []):
        if t >= float(marker.get("time", 0.0)):
            state = str(marker.get("state", state))
        else:
            break
    return state
