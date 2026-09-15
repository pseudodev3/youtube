from __future__ import annotations

import json
from pathlib import Path


TITLE_PATTERNS = {
    "rival_blockade": [
        "{rival} Would NOT Let Red Through 💀 | EP {episode}",
        "Red Got Boxed In by {rival} | EP {episode}",
        "{rival} Shut Every Door on Red | EP {episode}",
        "Red Could Not Escape {rival} | EP {episode}",
    ],
    "revenge": [
        "Red Wanted Revenge on {rival} | EP {episode}",
        "Red Came Back for {rival} | EP {episode}",
        "This Beef With {rival} Got Worse | EP {episode}",
        "Red Had Not Forgotten {rival} | EP {episode}",
    ],
    "pileup_escape": [
        "The Grid Turned Into a Parking Lot 😭 | EP {episode}",
        "Red Drove Straight Into Chaos | EP {episode}",
        "Everybody Lost Their Minds at {track} | EP {episode}",
        "Red Somehow Survived This Mess | EP {episode}",
    ],
    "comeback": [
        "Red Had to Do This the Hard Way | EP {episode}",
        "Red's Comeback Got Messy Fast | EP {episode}",
        "Red Refused to Stay at the Back | EP {episode}",
        "The Comeback Went VERY Wrong | EP {episode}",
    ],
    "clean_duel": [
        "Red vs {rival}. No Excuses. | EP {episode}",
        "Red and {rival} Went Side by Side | EP {episode}",
        "Nobody Blinked in Red vs {rival} | EP {episode}",
        "Red Had One Clean Shot at {rival} | EP {episode}",
    ],
    "chaos_race": [
        "Nobody on This Grid Can Be Normal 💀 | EP {episode}",
        "This Race Completely Lost the Plot | EP {episode}",
        "24 Seconds of Terrible Decisions | EP {episode}",
        "The Whole Grid Chose Chaos | EP {episode}",
    ],
    "showdown": [
        "Red and {rival} Finally Settle It | EP {episode}",
        "The Red vs {rival} Showdown | EP {episode}",
        "This Rivalry Had to End on Track | EP {episode}",
        "Red Put Everything on the Line vs {rival} | EP {episode}",
    ],
}


def build_metadata(plan: dict, telemetry: dict, video_path: Path) -> dict:
    episode = int(plan.get("episode", 1))
    rival = str(plan.get("featured_rival", "BLUE")).title()
    story_type = str(plan.get("story_type", "rival_blockade"))
    position = int(telemetry.get("final_position", 8))
    target = int(plan.get("target_position", 4))
    track = plan.get("track", {})
    track_name = str(track.get("name", "the circuit"))
    track_short = track_name.split(" — ", 1)[0]
    cleared = position <= target

    patterns = TITLE_PATTERNS.get(story_type, ["Red Survived Another Race | EP {episode}"])
    pattern = patterns[(episode - 1) % len(patterns)]
    title = pattern.format(
        rival=rival,
        episode=episode,
        track=track_short,
        position=position,
        target=target,
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
