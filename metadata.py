from __future__ import annotations

import json
from pathlib import Path


TITLE_PATTERNS = {
    "rival_blockade": "{rival} Would NOT Let Red Through 💀 | EP {episode}",
    "revenge": "Red Wanted Revenge on {rival} | EP {episode}",
    "pileup_escape": "The Grid Turned Into a Parking Lot 😭 | EP {episode}",
    "comeback": "Red Had to Do This the Hard Way | EP {episode}",
    "clean_duel": "Red vs {rival}. No Excuses. | EP {episode}",
    "chaos_race": "Nobody on This Grid Can Be Normal 💀 | EP {episode}",
    "showdown": "Red and {rival} Finally Settle It | EP {episode}",
}


def build_metadata(plan: dict, telemetry: dict, video_path: Path) -> dict:
    episode = int(plan.get("episode", 1))
    rival = str(plan.get("featured_rival", "BLUE")).title()
    story_type = str(plan.get("story_type", "rival_blockade"))
    position = int(telemetry.get("final_position", 8))
    target = int(plan.get("target_position", 4))
    track = plan.get("track", {})
    track_name = str(track.get("name", "the circuit"))
    cleared = position <= target

    title = TITLE_PATTERNS.get(story_type, "Red Survived Another Race | EP {episode}").format(
        rival=rival,
        episode=episode,
    )
    if len(title) > 95:
        title = title[:92].rstrip() + "..."

    result_line = f"Red finished P{position} and {'cleared' if cleared else 'missed'} the P{target} target."
    description = (
        f"Episode {episode} of GRIDLOOP. {result_line}\n\n"
        f"Road: {track_name}\n"
        f"Featured rival: {rival}\n"
        f"Story: {plan.get('story_label', story_type)}\n\n"
        "Every race changes the next one: rivalries grow, harder roads unlock, and Red keeps learning.\n\n"
        "#racing #shorts #gridloop #motorsport"
    )

    tags = [
        "GRIDLOOP", "racing", "racing shorts", "motorsport", "formula racing",
        "procedural racing", "cartoon racing", rival, track.get("key", "circuit"),
    ]
    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": "20",
        "privacy_status": "public",
        "video": str(video_path),
        "episode": episode,
        "featured_rival": plan.get("featured_rival"),
        "track": track_name,
        "story_type": story_type,
        "final_position": position,
        "target_position": target,
    }


def write_metadata(metadata: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")
