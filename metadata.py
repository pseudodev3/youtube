from __future__ import annotations

import json
import re
from pathlib import Path

from track_system import ROAD_CATALOG


TITLE_PATTERNS = {
    "rival_blockade": [
        "{rival} Would NOT Let Red Through 💀 | EP {episode}",
        "Red Got Boxed In by {rival} | EP {episode}",
        "{rival} Shut Every Door on Red | EP {episode}",
        "Red Could Not Escape {rival} | EP {episode}",
        "{rival} Turned the Track Into a Wall | EP {episode}",
        "Every Gap Closed on Red vs {rival} | EP {episode}",
        "Red Spent the Whole Race Chasing {rival} | EP {episode}",
        "{rival} Made Red Work for Every Inch | EP {episode}",
    ],
    "revenge": [
        "Red Wanted Revenge on {rival} | EP {episode}",
        "Red Came Back for {rival} | EP {episode}",
        "This Beef With {rival} Got Worse | EP {episode}",
        "Red Had Not Forgotten {rival} | EP {episode}",
        "Red Finally Got Another Shot at {rival} | EP {episode}",
        "{rival} Knew Red Was Coming Back | EP {episode}",
        "Red Brought the Rivalry Back to the Track | EP {episode}",
        "Round Two With {rival} Got Personal | EP {episode}",
    ],
    "pileup_escape": [
        "The Grid Turned Into a Parking Lot 😭 | EP {episode}",
        "Red Drove Straight Into Chaos | EP {episode}",
        "Everybody Lost Their Minds at {track} | EP {episode}",
        "Red Somehow Survived This Mess | EP {episode}",
        "There Was Nowhere Safe on This Track | EP {episode}",
        "Red Picked a Path Through the Wreckage | EP {episode}",
        "This Race Fell Apart in Seconds | EP {episode}",
        "The Pack Imploded Around Red | EP {episode}",
    ],
    "comeback": [
        "Red Had to Do This the Hard Way | EP {episode}",
        "Red's Comeback Got Messy Fast | EP {episode}",
        "Red Refused to Stay at the Back | EP {episode}",
        "The Comeback Went VERY Wrong | EP {episode}",
        "Red Started Buried and Kept Coming | EP {episode}",
        "The Grid Thought Red Was Finished | EP {episode}",
        "Red Had One Race to Fix the Damage | EP {episode}",
        "Red Would Not Accept P{position} | EP {episode}",
    ],
    "clean_duel": [
        "Red vs {rival}. No Excuses. | EP {episode}",
        "Red and {rival} Went Side by Side | EP {episode}",
        "Nobody Blinked in Red vs {rival} | EP {episode}",
        "Red Had One Clean Shot at {rival} | EP {episode}",
        "One Corner Decided Red vs {rival} | EP {episode}",
        "Red and {rival} Refused to Lift | EP {episode}",
        "This Was Pure Red vs {rival} | EP {episode}",
        "{rival} Gave Red Absolutely Nothing | EP {episode}",
    ],
    "chaos_race": [
        "Nobody on This Grid Can Be Normal 💀 | EP {episode}",
        "This Race Completely Lost the Plot | EP {episode}",
        "24 Seconds of Terrible Decisions | EP {episode}",
        "The Whole Grid Chose Chaos | EP {episode}",
        "Every Driver Made the Wrong Choice | EP {episode}",
        "Red Somehow Raced Through All of This | EP {episode}",
        "The Grid Went Full Chaos Mode | EP {episode}",
        "This Was Not a Normal Race | EP {episode}",
    ],
    "showdown": [
        "Red and {rival} Finally Settle It | EP {episode}",
        "The Red vs {rival} Showdown | EP {episode}",
        "This Rivalry Had to End on Track | EP {episode}",
        "Red Put Everything on the Line vs {rival} | EP {episode}",
        "No More Excuses: Red vs {rival} | EP {episode}",
        "Red and {rival} Finally Got Their Race | EP {episode}",
        "This Was the Race Red Owed {rival} | EP {episode}",
        "Only One of Them Was Backing Out | EP {episode}",
    ],
}

# These are the original four-template pools used by episodes before title memory
# existed. They let us reconstruct old generated titles from career history.
LEGACY_TITLE_PATTERNS = {story: patterns[:4] for story, patterns in TITLE_PATTERNS.items()}

# This wording already appeared multiple times in the live series. Retire it
# permanently instead of waiting for the recent-history window to expire.
RETIRED_TITLE_STEMS = {
    "red had to do this the hard way",
}


def _title_stem(title: str) -> str:
    stem = re.sub(r"\s*\|\s*EP\s*\d+\s*$", "", str(title), flags=re.IGNORECASE)
    stem = re.sub(r"[^a-z0-9]+", " ", stem.lower()).strip()
    return re.sub(r"\s+", " ", stem)


def _legacy_title(entry: dict) -> str | None:
    story_type = str(entry.get("story_type", ""))
    patterns = LEGACY_TITLE_PATTERNS.get(story_type)
    if not patterns:
        return None

    episode = int(entry.get("episode", 0) or 0)
    rival = str(entry.get("featured_rival", "BLUE")).title()
    track_key = str(entry.get("track", "training"))
    track_short = str(ROAD_CATALOG.get(track_key, {}).get("display", track_key or "the circuit"))
    position = int(entry.get("final_position", 8) or 8)
    target = int(entry.get("target_position", 4) or 4)
    pattern = patterns[(max(1, episode) - 1) % len(patterns)]
    return pattern.format(
        rival=rival,
        episode=episode,
        track=track_short,
        position=position,
        target=target,
    )


def _recent_title_stems(career: dict | None) -> set[str]:
    used = set(RETIRED_TITLE_STEMS)
    if not career:
        return used

    for entry in career.get("history", [])[-18:]:
        title = entry.get("title") or _legacy_title(entry)
        if title:
            used.add(_title_stem(str(title)))
    return used


def _choose_title(plan: dict, telemetry: dict, career: dict | None) -> str:
    episode = int(plan.get("episode", 1))
    rival = str(plan.get("featured_rival", "BLUE")).title()
    story_type = str(plan.get("story_type", "rival_blockade"))
    position = int(telemetry.get("final_position", 8))
    target = int(plan.get("target_position", 4))
    track = plan.get("track", {})
    track_name = str(track.get("name", "the circuit"))
    track_short = track_name.split(" — ", 1)[0]

    patterns = TITLE_PATTERNS.get(story_type, ["Red Survived Another Race | EP {episode}"])
    used = _recent_title_stems(career)

    seed = int(plan.get("seed", episode * 1009))
    start = (seed + episode * 17) % len(patterns)
    ordered = patterns[start:] + patterns[:start]

    for pattern in ordered:
        candidate = pattern.format(
            rival=rival,
            episode=episode,
            track=track_short,
            position=position,
            target=target,
        )
        if _title_stem(candidate) not in used:
            return candidate[:95] if len(candidate) <= 95 else candidate[:92].rstrip() + "..."

    # Extremely defensive fallback once a story's entire phrase bank has been used.
    candidate = f"Red vs {rival} at {track_short}: P{position} Finish | EP {episode}"
    return candidate[:95] if len(candidate) <= 95 else candidate[:92].rstrip() + "..."


def build_metadata(plan: dict, telemetry: dict, video_path: Path, career: dict | None = None) -> dict:
    episode = int(plan.get("episode", 1))
    rival = str(plan.get("featured_rival", "BLUE")).title()
    story_type = str(plan.get("story_type", "rival_blockade"))
    position = int(telemetry.get("final_position", 8))
    target = int(plan.get("target_position", 4))
    track = plan.get("track", {})
    track_name = str(track.get("name", "the circuit"))
    cleared = position <= target

    title = _choose_title(plan, telemetry, career)

    result_line = f"Red finished P{position} and {'cleared' if cleared else 'missed'} the P{target} target."
    hook = str(plan.get("hook", "")).strip()
    opening = hook if hook else f"{plan.get('story_label', story_type)} at {track_name}."

    description = (
        f"Episode {episode} of GRIDLOOP. {opening}\n\n"
        f"{result_line}\n\n"
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
