from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from track_system import unlocked_roads

CAREER_PATH = Path("career_state.json")
LEGACY_STATE_PATH = Path("state.json")
DRIVERS = ["BLUE", "GREEN", "ORANGE", "PURPLE", "WHITE", "CYAN", "LIME"]


def _default_rivals() -> dict:
    return {
        name: {
            "rivalry": 1,
            "wins_over_red": 0,
            "losses_to_red": 0,
            "incidents": 0,
            "last_featured_episode": -999,
            "last_result": None,
        }
        for name in DRIVERS
    }


def default_career() -> dict:
    return {
        "version": 2,
        "episode": 1,
        "driver_skill": 0.20,
        "road_tier": 1,
        "car_tier": 2,
        "wins": 0,
        "crashes": 0,
        "uploads": 0,
        "unlocked_roads": ["training"],
        "last_track": None,
        "last_story": None,
        "last_result": None,
        "last_featured_rival": None,
        "last_video_id": None,
        "last_title": None,
        "rivals": _default_rivals(),
        "history": [],
    }


def _migrate_legacy(legacy: dict) -> dict:
    career = default_career()
    for key in ("episode", "driver_skill", "road_tier", "car_tier", "wins", "crashes"):
        if key in legacy:
            career[key] = legacy[key]
    career["unlocked_roads"] = unlocked_roads(float(career["driver_skill"]))
    return career


def normalize_career(career: dict) -> dict:
    base = default_career()
    merged = deepcopy(base)
    for key, value in career.items():
        if key != "rivals":
            merged[key] = value

    rivals = _default_rivals()
    for name, payload in career.get("rivals", {}).items():
        if name in rivals and isinstance(payload, dict):
            rivals[name].update(payload)
    merged["rivals"] = rivals
    merged["unlocked_roads"] = unlocked_roads(float(merged.get("driver_skill", 0.2)))
    merged["road_tier"] = max(1, len(merged["unlocked_roads"]))
    merged["car_tier"] = min(6, 1 + int(float(merged["driver_skill"]) * 6))
    merged["history"] = list(merged.get("history", []))[-30:]
    merged["version"] = 2
    return merged


def load_career() -> dict:
    if CAREER_PATH.exists():
        with CAREER_PATH.open("r", encoding="utf-8") as f:
            return normalize_career(json.load(f))
    if LEGACY_STATE_PATH.exists():
        with LEGACY_STATE_PATH.open("r", encoding="utf-8") as f:
            return normalize_career(_migrate_legacy(json.load(f)))
    return default_career()


def save_career(career: dict) -> None:
    career = normalize_career(career)
    with CAREER_PATH.open("w", encoding="utf-8") as f:
        json.dump(career, f, indent=2)
        f.write("\n")


def apply_uploaded_episode(
    career: dict,
    plan: dict,
    telemetry: dict,
    video_id: str,
    metadata: dict | None = None,
) -> dict:
    """Advance continuity only after YouTube returns a video id."""
    out = normalize_career(deepcopy(career))
    position = int(telemetry.get("final_position", 8))
    target = int(plan.get("target_position", 4))
    crashed = bool(telemetry.get("player_crashed", False))
    cleared = position <= target

    skill = float(out.get("driver_skill", 0.2))
    gain = 0.020 if crashed else (0.032 if cleared else 0.025)
    out["driver_skill"] = round(min(0.985, skill + gain), 3)
    out["episode"] = int(out.get("episode", 1)) + 1
    out["uploads"] = int(out.get("uploads", 0)) + 1
    out["wins"] = int(out.get("wins", 0)) + int(cleared)
    out["crashes"] = int(out.get("crashes", 0)) + int(crashed)
    out["last_result"] = "target_cleared" if cleared else "target_missed"
    out["last_story"] = plan.get("story_type")
    out["last_track"] = plan.get("track", {}).get("key")
    out["last_featured_rival"] = plan.get("featured_rival")
    out["last_video_id"] = video_id
    if metadata and metadata.get("title"):
        out["last_title"] = str(metadata["title"])

    featured = str(plan.get("featured_rival", "BLUE"))
    rival = out["rivals"].setdefault(featured, _default_rivals().get(featured, {}))
    rival["last_featured_episode"] = int(plan.get("episode", out["episode"] - 1))
    incidents = int(telemetry.get("featured_contact_events", 0))
    rival["incidents"] = int(rival.get("incidents", 0)) + incidents

    if cleared:
        rival["losses_to_red"] = int(rival.get("losses_to_red", 0)) + 1
        rival["rivalry"] = max(1, int(rival.get("rivalry", 1)) - (1 if incidents == 0 else 0))
        rival["last_result"] = "red_won"
    else:
        rival["wins_over_red"] = int(rival.get("wins_over_red", 0)) + 1
        rival["rivalry"] = min(10, int(rival.get("rivalry", 1)) + 1 + int(incidents > 0))
        rival["last_result"] = "rival_won"

    entry = {
        "episode": int(plan.get("episode", out["episode"] - 1)),
        "video_id": video_id,
        "story_type": plan.get("story_type"),
        "track": plan.get("track", {}).get("key"),
        "featured_rival": featured,
        "final_position": position,
        "target_position": target,
        "result": out["last_result"],
        "crashed": crashed,
        "events": int(telemetry.get("event_count", 0)),
        "title": str(metadata.get("title")) if metadata and metadata.get("title") else None,
    }
    out["history"] = (list(out.get("history", [])) + [entry])[-30:]
    return normalize_career(out)
