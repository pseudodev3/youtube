from __future__ import annotations

from copy import deepcopy

from captioning import CaptionDirector, action_candidates, hook_candidates


STORY_TEMPLATES = {
    "rival_blockade": {
        "label": "Rival blockade",
        "hooks": [
            "{rival} WOULD NOT LET RED THROUGH",
            "RED HAD ONE PROBLEM: {rival}",
            "{rival} PARKED THE BUS AGAIN",
        ],
        "beats": [
            (3.2, "featured", "block", "{rival} SHUTS THE DOOR"),
            (6.8, "featured", "brake_check", "{rival} BRAKE CHECKS RED?!"),
            (10.7, "random", "swerve", "CHAOS BEHIND THEM"),
            (15.4, "featured", "divebomb", "{rival} COMES BACK FOR MORE"),
            (20.0, "featured", "block", "ONE LAST FIGHT"),
        ],
    },
    "revenge": {
        "label": "Revenge race",
        "hooks": [
            "RED WANTED REVENGE ON {rival}",
            "{rival} REMEMBERED LAST RACE",
            "THIS BEEF IS GETTING PERSONAL",
        ],
        "beats": [
            (3.0, "featured", "swerve", "{rival} FIRES THE FIRST SHOT"),
            (7.2, "featured", "block", "NO ROOM FROM {rival}"),
            (11.3, "random", "spin", "SOMEONE THROWS IT AWAY"),
            (16.0, "featured", "divebomb", "{rival} SENDS IT"),
            (20.4, "featured", "brake_check", "FINAL-LAP DRAMA"),
        ],
    },
    "pileup_escape": {
        "label": "Pileup escape",
        "hooks": [
            "THE GRID TURNED INTO A PARKING LOT",
            "RED HAD TO SURVIVE THIS ONE",
            "THIS RACE GOT STUPID FAST",
        ],
        "beats": [
            (3.6, "random", "swerve", "IT STARTS GETTING MESSY"),
            (7.0, "featured", "divebomb", "{rival} SEES A GAP"),
            (10.0, "random", "spin", "CAR SIDEWAYS!"),
            (13.0, "random", "divebomb", "THEY ARRIVE TOO FAST"),
            (18.3, "featured", "swerve", "RED HAS TO PICK A GAP"),
        ],
    },
    "comeback": {
        "label": "Comeback",
        "hooks": [
            "RED HAD TO DO THIS THE HARD WAY",
            "FROM THE BACK OF THE GRID",
            "THE COMEBACK STARTS NOW",
        ],
        "beats": [
            (3.4, "random", "brake_check", "RED GETS HELD UP"),
            (7.4, "featured", "block", "{rival} MAKES IT WORSE"),
            (11.7, "random", "panic", "A GAP OPENS"),
            (15.8, "featured", "swerve", "RED CLOSES BACK IN"),
            (20.1, "featured", "divebomb", "ONE LAST POSITION"),
        ],
    },
    "clean_duel": {
        "label": "Clean duel",
        "hooks": [
            "RED VS {rival}. NO EXCUSES.",
            "JUST RED AND {rival} THIS TIME",
            "THE CLEANEST FIGHT ON THE GRID",
        ],
        "beats": [
            (3.5, "featured", "block", "{rival} DEFENDS"),
            (8.0, "featured", "swerve", "RED LOOKS AROUND THE OUTSIDE"),
            (13.0, "featured", "block", "STILL SIDE BY SIDE"),
            (18.0, "featured", "divebomb", "{rival} ANSWERS BACK"),
            (21.0, "featured", "block", "LAST CHANCE"),
        ],
    },
    "chaos_race": {
        "label": "Chaos race",
        "hooks": [
            "NOBODY ON THIS GRID CAN BE NORMAL",
            "THIS RACE LOST THE PLOT",
            "24 SECONDS OF TERRIBLE DECISIONS",
        ],
        "beats": [
            (3.0, "random", "showboat", "WHY WOULD YOU DO THAT?"),
            (6.3, "random", "brake_check", "BRAKES!"),
            (9.8, "random", "spin", "THERE GOES ONE"),
            (14.2, "featured", "divebomb", "{rival} JOINS THE NONSENSE"),
            (19.0, "random", "swerve", "ABSOLUTE SCENES"),
        ],
    },
    "showdown": {
        "label": "Rival showdown",
        "hooks": [
            "RED AND {rival} FINALLY SETTLE IT",
            "THE {rival} SHOWDOWN",
            "THIS RIVALRY ENDS ON TRACK",
        ],
        "beats": [
            (3.0, "featured", "block", "{rival} STARTS DEFENDING EARLY"),
            (6.5, "featured", "divebomb", "FIRST BIG MOVE"),
            (10.5, "random", "spin", "TRAFFIC CHANGES EVERYTHING"),
            (14.7, "featured", "swerve", "THEY FIND EACH OTHER AGAIN"),
            (19.2, "featured", "divebomb", "THIS IS FOR THE RIVALRY"),
        ],
    },
}


def choose_story_type(rng, career: dict, featured_rival: str) -> str:
    rivals = career.get("rivals", {})
    rivalry = int(rivals.get(featured_rival, {}).get("rivalry", 1))
    last_story = career.get("last_story")
    recent = [h.get("story_type") for h in career.get("history", [])[-4:]]

    if rivalry >= 7 and "showdown" not in recent:
        return "showdown"
    if career.get("last_result") == "target_missed" and "comeback" not in recent:
        return "comeback"

    weighted = [
        "rival_blockade",
        "revenge" if rivalry >= 3 else "clean_duel",
        "pileup_escape",
        "comeback",
        "clean_duel",
        "chaos_race",
    ]
    choices = [x for x in weighted if x != last_story]
    return rng.choice(choices or weighted)


def build_story(
    story_type: str,
    rival: str,
    rng,
    duration: float = 24.0,
    episode: int = 1,
    seed: int = 0,
    used_caption_hashes=None,
) -> dict:
    template = deepcopy(STORY_TEMPLATES[story_type])
    director = CaptionDirector(seed=seed ^ 0x51A7, episode=episode, used_hashes=used_caption_hashes)
    hook = director.fresh(
        hook_candidates(story_type, rival, template["hooks"]),
        category=f"hook:{story_type}",
    )
    beats = []
    for t, actor, action, caption in template["beats"]:
        if t >= duration - 1.8:
            continue
        fresh_caption = director.fresh(
            action_candidates(action, rival, caption),
            category=f"story:{story_type}:{action}",
        )
        beats.append({
            "time": round(float(t), 2),
            "actor": actor,
            "driver": rival if actor == "featured" else None,
            "action": action,
            "caption": fresh_caption,
        })
    return {
        "type": story_type,
        "label": template["label"],
        "hook": hook,
        "beats": beats,
    }
