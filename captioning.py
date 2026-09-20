from __future__ import annotations

import hashlib
import random
import re
from typing import Iterable


def normalize_caption(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip()).upper()


def caption_hash(text: str) -> str:
    return hashlib.sha1(normalize_caption(text).encode("utf-8")).hexdigest()[:16]


# Reserve the pre-CaptionDirector vocabulary too. Those episodes were rendered
# before persistent caption hashes existed, so the Railway career volume cannot
# tell us exactly which old stock lines appeared. Reserving the whole legacy set
# is safer than letting any of them resurface.
_LEGACY_RIVALS = ("BLUE", "GREEN", "ORANGE", "PURPLE", "WHITE", "CYAN", "LIME")
_LEGACY_PATTERNS = (
    "{rival} WOULD NOT LET RED THROUGH", "RED HAD ONE PROBLEM: {rival}",
    "{rival} PARKED THE BUS AGAIN", "{rival} SHUTS THE DOOR",
    "{rival} BRAKE CHECKS RED?!", "CHAOS BEHIND THEM",
    "{rival} COMES BACK FOR MORE", "ONE LAST FIGHT",
    "RED WANTED REVENGE ON {rival}", "{rival} REMEMBERED LAST RACE",
    "THIS BEEF IS GETTING PERSONAL", "{rival} FIRES THE FIRST SHOT",
    "NO ROOM FROM {rival}", "SOMEONE THROWS IT AWAY", "{rival} SENDS IT",
    "FINAL-LAP DRAMA", "THE GRID TURNED INTO A PARKING LOT",
    "RED HAD TO SURVIVE THIS ONE", "THIS RACE GOT STUPID FAST",
    "IT STARTS GETTING MESSY", "{rival} SEES A GAP", "CAR SIDEWAYS!",
    "THEY ARRIVE TOO FAST", "RED HAS TO PICK A GAP",
    "RED HAD TO DO THIS THE HARD WAY", "FROM THE BACK OF THE GRID",
    "THE COMEBACK STARTS NOW", "RED GETS HELD UP", "{rival} MAKES IT WORSE",
    "A GAP OPENS", "RED CLOSES BACK IN", "ONE LAST POSITION",
    "RED VS {rival}. NO EXCUSES.", "JUST RED AND {rival} THIS TIME",
    "THE CLEANEST FIGHT ON THE GRID", "{rival} DEFENDS",
    "RED LOOKS AROUND THE OUTSIDE", "STILL SIDE BY SIDE",
    "{rival} ANSWERS BACK", "LAST CHANCE", "NOBODY ON THIS GRID CAN BE NORMAL",
    "THIS RACE LOST THE PLOT", "24 SECONDS OF TERRIBLE DECISIONS",
    "WHY WOULD YOU DO THAT?", "BRAKES!", "THERE GOES ONE",
    "{rival} JOINS THE NONSENSE", "ABSOLUTE SCENES",
    "RED AND {rival} FINALLY SETTLE IT", "THE {rival} SHOWDOWN",
    "THIS RIVALRY ENDS ON TRACK", "{rival} STARTS DEFENDING EARLY",
    "FIRST BIG MOVE", "TRAFFIC CHANGES EVERYTHING",
    "THEY FIND EACH OTHER AGAIN", "THIS IS FOR THE RIVALRY",
    "HUGE HIT! 💥", "FULL SPIN!", "THAT'S A CRASH!", "WHEEL TO WHEEL!",
    "THEY TOUCH!", "NO ROOM!", "RUBBING WHEELS", "RED GETS ONE!",
    "RED SNEAKS THROUGH!", "CLEAN PASS!", "RED CATCHES THE SLIDE!",
    "COUNTERSTEER!", "HE SAVED IT!", "RED THREW IT AWAY!", "TOO MUCH!",
    "NO GRIP!", "RED'S BACK!", "BIG CONTACT! 💥", "RED RUBS WHEELS!",
    "NO SPACE!",
)


def _legacy_reserved_hashes() -> set[str]:
    hashes: set[str] = set()
    for pattern in _LEGACY_PATTERNS:
        if "{rival}" in pattern:
            for rival in _LEGACY_RIVALS:
                hashes.add(caption_hash(pattern.format(rival=rival)))
        else:
            hashes.add(caption_hash(pattern))
    for rival in _LEGACY_RIVALS:
        hashes.add(caption_hash(f"{rival} GETS RED!"))
        hashes.add(caption_hash(f"RED AND {rival} CRASH! 💥"))
        hashes.add(caption_hash(f"RED AND {rival} MAKE CONTACT!"))
        hashes.add(caption_hash(f"RED RUBS {rival}'S WHEEL"))
    for position in range(1, 9):
        hashes.add(caption_hash(f"TARGET CLEARED! P{position} 🔥"))
    for missed in range(1, 8):
        noun = "PLACE" if missed == 1 else "PLACES"
        hashes.add(caption_hash(f"MISSED BY {missed} {noun}"))
    return hashes


LEGACY_RESERVED_HASHES = _legacy_reserved_hashes()


HOOK_BANKS = {
    "rival_blockade": [
        "{rival} WOULD NOT LET RED THROUGH",
        "RED HAD ONE PROBLEM: {rival}",
        "{rival} PARKED THE BUS AGAIN",
        "{rival} CLOSED EVERY DOOR",
        "RED COULD NOT SHAKE {rival}",
        "{rival} TURNED THIS INTO A WALL",
        "EVERY GAP HAD {rival} IN IT",
        "RED NEEDED ONE CLEAN LOOK AT {rival}",
        "{rival} MADE THE ROAD FEEL TINY",
        "THIS WAS RED VS {rival}'S DEFENCE",
    ],
    "revenge": [
        "RED WANTED REVENGE ON {rival}",
        "{rival} REMEMBERED LAST RACE",
        "THIS BEEF IS GETTING PERSONAL",
        "RED CAME BACK FOR {rival}",
        "{rival} WAS NOT GETTING A FREE PASS",
        "THE SCORE WITH {rival} WAS NOT SETTLED",
        "RED HAD NOT FORGOTTEN {rival}",
        "THIS ONE STARTED WITH BAD BLOOD",
        "{rival} AND RED HAD HISTORY",
        "RED WANTED THIS ONE BACK",
    ],
    "pileup_escape": [
        "THE GRID TURNED INTO A PARKING LOT",
        "RED HAD TO SURVIVE THIS ONE",
        "THIS RACE GOT STUPID FAST",
        "EVERYTHING WENT WRONG AT ONCE",
        "RED DROVE STRAIGHT INTO CHAOS",
        "THE GRID FORGOT HOW TO BE NORMAL",
        "THIS TURNED INTO SURVIVAL MODE",
        "RED NEEDED A WAY THROUGH THE MESS",
        "NOBODY LEFT RED A CLEAN ROAD",
        "THE RACE COLLAPSED AROUND RED",
    ],
    "comeback": [
        "RED HAD TO DO THIS THE HARD WAY",
        "FROM THE BACK OF THE GRID",
        "THE COMEBACK STARTS NOW",
        "RED REFUSED TO STAY BURIED",
        "EVERY POSITION HAD TO BE EARNED",
        "RED HAD A LONG WAY BACK",
        "THIS WAS ALL ABOUT THE RECOVERY",
        "RED STARTED WITH WORK TO DO",
        "THE ONLY WAY WAS FORWARD",
        "RED NEEDED A REAL COMEBACK",
    ],
    "clean_duel": [
        "RED VS {rival}. NO EXCUSES.",
        "JUST RED AND {rival} THIS TIME",
        "THE CLEANEST FIGHT ON THE GRID",
        "ONE ROAD. RED. {rival}.",
        "RED AND {rival} KEPT IT CLEAN",
        "THIS WAS PURE RED VS {rival}",
        "NO CHAOS. JUST RED AND {rival}",
        "RED GOT ONE FAIR SHOT AT {rival}",
        "THE GRID LEFT RED AND {rival} ALONE",
        "THIS ONE CAME DOWN TO TWO CARS",
    ],
    "chaos_race": [
        "NOBODY ON THIS GRID CAN BE NORMAL",
        "THIS RACE LOST THE PLOT",
        "24 SECONDS OF TERRIBLE DECISIONS",
        "THE GRID CHOSE CHAOS AGAIN",
        "NOTHING ABOUT THIS RACE MADE SENSE",
        "RED GOT THE WEIRDEST RACE POSSIBLE",
        "EVERYONE MADE A BAD DECISION",
        "THIS ONE WENT OFF THE RAILS FAST",
        "THE GRID WAS FEELING UNHINGED",
        "RED HAD TO RACE THROUGH NONSENSE",
    ],
    "showdown": [
        "RED AND {rival} FINALLY SETTLE IT",
        "THE {rival} SHOWDOWN",
        "THIS RIVALRY ENDS ON TRACK",
        "RED AND {rival} HAD TO FINISH THIS",
        "THIS WAS THE ONE WITH {rival}",
        "NO MORE TALK. RED VS {rival}.",
        "THE RIVALRY CAME BACK TO THE ROAD",
        "RED PUT IT ALL ON {rival}",
        "{rival} GOT ONE LAST SHOT AT RED",
        "THIS FIGHT HAD BEEN BUILDING",
    ],
}


ACTION_BANKS = {
    "block": [
        "{rival} SHUTS THE DOOR", "{rival} COVERS THE INSIDE",
        "{rival} LEAVES NO ROAD", "{rival} MAKES RED GO LONG",
        "THE DOOR CLOSES AGAIN", "RED FINDS NO GAP",
        "{rival} HOLDS THE LINE", "RED GETS BOXED OUT",
        "{rival} DEFENDS IT HARD", "NO EASY WAY PAST {rival}",
    ],
    "brake_check": [
        "{rival} HITS THE BRAKES", "{rival} CHECKS RED UP",
        "RED HAS TO LIFT", "BRAKES RIGHT IN FRONT OF RED",
        "{rival} KILLS THE RUN", "RED GETS CAUGHT OUT",
        "THAT BRAKE ZONE GETS UGLY", "RED HAS TO REACT FAST",
        "{rival} SLOWS IT DOWN HARD", "THE GAP DISAPPEARS UNDER BRAKING",
    ],
    "swerve": [
        "{rival} MOVES ACROSS", "THE LINE CHANGES FAST",
        "RED HAS TO PICK A SIDE", "THE ROAD GETS CROWDED",
        "{rival} MAKES IT MESSY", "RED CHANGES THE PLAN",
        "THE GAP MOVES AGAIN", "NO STRAIGHTFORWARD WAY THROUGH",
        "{rival} THROWS A MOVE ACROSS", "RED HAS TO READ IT",
    ],
    "divebomb": [
        "{rival} SENDS IT", "{rival} DIVES FOR THE GAP",
        "LATE MOVE FROM {rival}", "{rival} COMMITS FROM WAY BACK",
        "RED GETS A CAR THROWN INSIDE", "{rival} GOES ALL IN",
        "THAT MOVE CAME FROM NOWHERE", "{rival} BRAKES LATE",
        "RED HAS TO COVER THE DIVE", "{rival} MAKES THE BIG MOVE",
    ],
    "spin": [
        "ONE CAR GOES AROUND", "SOMEONE LOSES THE REAR",
        "THE GRID GETS A SPIN", "A CAR TURNS SIDEWAYS",
        "THAT ONE IS GONE", "SOMEBODY OVERDOES IT",
        "THE REAR STEPS OUT", "ONE DRIVER THROWS IT AWAY",
        "A SPIN OPENS THE ROAD", "THE PACK HAS TO DODGE ONE",
    ],
    "panic": [
        "A GAP OPENS", "SOMEONE PANICS",
        "THE LINE BREAKS OPEN", "RED GETS A CHANCE",
        "THE PACK HESITATES", "RED SEES DAYLIGHT",
        "ONE MISTAKE OPENS EVERYTHING", "THE ROAD SUDDENLY CLEARS",
        "RED GETS THE WINDOW", "THE GRID BLINKS FIRST",
    ],
    "showboat": [
        "WHY WOULD YOU DO THAT", "SOMEONE GETS FANCY",
        "THE GRID STARTS SHOWING OFF", "THAT WAS COMPLETELY UNNECESSARY",
        "ONE DRIVER CHOOSES DRAMA", "THE RACE GETS SILLY",
        "SOMEBODY WANTS ATTENTION", "STYLE OVER SENSE",
        "THAT MOVE HELPS NOBODY", "THE GRID IS SHOWING OFF AGAIN",
    ],
}


PASS_BANK = [
    "RED GETS ONE", "RED SNEAKS THROUGH", "CLEAN PASS", "RED FINDS THE GAP",
    "RED SLIPS BY", "ONE MORE FOR RED", "RED MAKES IT STICK",
    "RED CLEARS ANOTHER CAR", "RED TAKES THE POSITION", "RED GETS THROUGH CLEAN",
    "THAT GAP WAS ENOUGH", "RED PICKS ONE OFF",
]

DRIFT_BANK = [
    "RED CATCHES THE SLIDE", "COUNTERSTEER", "HE SAVED IT",
    "RED HOLDS THE DRIFT", "THE REAR STEPS OUT", "RED KEEPS IT ALIVE",
    "THAT SLIDE STAYS CAUGHT", "RED RIDES IT OUT", "NO SPIN FOR RED",
    "RED GETS IT STRAIGHT", "THE CAR COMES BACK", "RED SAVES THE REAR",
]

CRASH_BANK = [
    "THAT'S A CRASH", "HUGE HIT", "FULL SPIN", "THEY HIT HARD",
    "CONTACT TURNS INTO CHAOS", "ONE CAR IS AROUND", "THAT ENDS BADLY",
    "THE PACK TAKES A HIT", "SOMEBODY GETS TURNED", "THAT CONTACT WAS HEAVY",
    "THE GRID BREAKS APART", "THAT ONE HURTS",
]

CONTACT_BANK = [
    "WHEEL TO WHEEL", "THEY TOUCH", "NO ROOM", "BIG CONTACT",
    "RED RUBS WHEELS", "NO SPACE", "THE CARS LEAN ON EACH OTHER",
    "THAT GAP WAS TOO SMALL", "THEY MAKE CONTACT", "THEY RUN OUT OF ROAD",
    "CAR AGAINST CAR", "THAT WAS TIGHT",
]

RECOVERY_BANK = [
    "RED'S BACK", "RED GETS GOING AGAIN", "RED REJOINS THE FIGHT",
    "THE RECOVERY IS ON", "RED IS MOVING AGAIN", "BACK IN THE RACE",
    "RED GETS IT TOGETHER", "THE COMEBACK CONTINUES",
]

GENERIC_LEADS = [
    "RED", "THE GRID", "THIS FIGHT", "THAT MOVE", "THE BATTLE",
    "THE RACE", "THE PACK", "THIS SECTOR", "THE ROAD", "THE CHASE",
]
GENERIC_VERBS = [
    "STAYS WILD", "KEEPS MOVING", "ISN'T OVER", "GETS TIGHTER",
    "GOES AGAIN", "TURNS MESSY", "OPENS UP", "GETS LOUD",
    "CHANGES FAST", "STAYS ON THE LIMIT", "BREAKS OPEN", "GETS SERIOUS",
]
GENERIC_TAILS = [
    "RIGHT HERE", "UNDER PRESSURE", "WITH NO ROOM", "AT FULL SEND",
    "ON THE LIMIT", "IN TRAFFIC", "THROUGH THE NEXT MOVE", "WITH EVERYTHING MOVING",
    "IN THE FIGHT", "WITH RED STILL IN IT", "IN THE BRAKING ZONE",
    "THROUGH THE CHAOS", "AT THE EDGE", "WITH THE PACK CLOSE",
    "BEFORE THE NEXT CORNER", "WITH NO TIME TO WAIT", "WHILE THE GAP IS OPEN",
    "WITH EVERYTHING ON THE LINE",
]

GENERIC_FINISHES = [
    "", "AGAIN", "THIS TIME", "ONE MORE TIME", "WITHOUT LIFTING",
    "AND RED STAYS IN IT", "AND THE PACK RESPONDS", "WITH NO EASY EXIT",
    "BEFORE IT CLOSES", "AS THE ROAD TIGHTENS", "WITH THE FIELD ATTACHED",
    "AND NOBODY BACKS OUT", "WHILE THE PRESSURE BUILDS", "AT RACE SPEED",
    "WITH THE NEXT MOVE COMING", "AND IT STILL ISN'T SETTLED",
]


def _format_all(items: Iterable[str], rival: str) -> list[str]:
    return [str(x).format(rival=rival) for x in items]


def hook_candidates(story_type: str, rival: str, fallback: Iterable[str]) -> list[str]:
    bank = HOOK_BANKS.get(story_type, list(fallback))
    return _format_all(bank, rival)


def action_candidates(action: str, rival: str, fallback: str) -> list[str]:
    bank = ACTION_BANKS.get(action)
    if not bank:
        return [str(fallback).format(rival=rival)]
    candidates = [str(fallback).format(rival=rival)]
    candidates.extend(_format_all(bank, rival))
    return list(dict.fromkeys(candidates))


def runtime_candidates(raw: str) -> list[str]:
    text = normalize_caption(raw)

    if "TARGET CLEARED" in text:
        pos = re.search(r"P(\d+)", text)
        p = f"P{pos.group(1)}" if pos else "THE TARGET"
        return [
            f"TARGET SECURED! {p}", f"JOB DONE! {p}", f"RED HITS THE TARGET! {p}",
            f"{p} IS ENOUGH!", f"TARGET CLEARED AT {p}", f"RED GETS IT DONE! {p}",
            f"MISSION COMPLETE! {p}", f"RED MAKES THE TARGET! {p}",
        ]
    if text.startswith("MISSED BY"):
        suffix = text.replace("MISSED BY", "").strip()
        return [
            f"MISSED BY {suffix}", f"JUST SHORT — {suffix}", f"RED COMES UP {suffix} SHORT",
            f"NOT QUITE — {suffix}", f"THE TARGET GETS AWAY BY {suffix}",
        ]
    if any(x in text for x in ("RED GETS ONE", "SNEAKS THROUGH", "CLEAN PASS")):
        return PASS_BANK
    if any(x in text for x in ("CATCHES THE SLIDE", "COUNTERSTEER", "SAVED IT", "NO GRIP")):
        return DRIFT_BANK
    if any(x in text for x in ("CRASH", "HUGE HIT", "FULL SPIN", "PILEUP", "THREW IT AWAY")):
        return [raw, *CRASH_BANK]
    if any(x in text for x in ("CONTACT", "WHEEL", "NO ROOM", "NO SPACE", "THEY TOUCH")):
        return [raw, *CONTACT_BANK]
    if "RED'S BACK" in text:
        return RECOVERY_BANK
    if " GETS RED" in text:
        rival = text.split(" GETS RED", 1)[0]
        return [
            f"{rival} GETS RED", f"{rival} TAKES IT BACK", f"{rival} RE-PASSES RED",
            f"{rival} GETS THE POSITION", f"RED LOSES ONE TO {rival}",
            f"{rival} SLIPS BACK THROUGH",
        ]
    return [raw]


class CaptionDirector:
    """Deterministic caption chooser with persistent all-time hash memory."""

    def __init__(
        self,
        seed: int,
        episode: int,
        used_hashes: Iterable[str] | None = None,
    ):
        self.seed = int(seed)
        self.episode = int(episode)
        self.used_hashes = set(LEGACY_RESERVED_HASHES)
        self.used_hashes.update(str(x) for x in (used_hashes or []))
        self.local_texts: set[str] = set()
        self.counter = 0

    def reserve(self, text: str) -> None:
        cleaned = normalize_caption(text)
        if cleaned:
            self.local_texts.add(cleaned)

    def _available(self, text: str) -> bool:
        cleaned = normalize_caption(text)
        return bool(cleaned) and cleaned not in self.local_texts and caption_hash(cleaned) not in self.used_hashes

    def fresh(self, candidates: Iterable[str], category: str = "caption") -> str:
        pool = [normalize_caption(x) for x in candidates if normalize_caption(x)]
        pool = list(dict.fromkeys(pool))
        if not pool:
            pool = ["THE RACE KEEPS MOVING"]

        keyed = random.Random(self.seed ^ (self.counter * 104729) ^ int(hashlib.sha1(category.encode()).hexdigest()[:8], 16))
        keyed.shuffle(pool)
        self.counter += 1

        for text in pool:
            if self._available(text):
                self.reserve(text)
                return text

        # Deep fallback stays anchored to the same semantic event. We vary an
        # authored candidate rather than switching to unrelated generic race copy,
        # so a pass is always captioned as a pass, a crash as a crash, etc.
        modifiers = (
            "AGAIN", "THIS TIME", "UNDER PRESSURE", "AT THE LIMIT",
            "WITH NO ROOM", "AT RACE SPEED", "WHEN IT COUNTS",
            "IN TRAFFIC", "ON THE ATTACK", "IN THE BRAKING ZONE",
            "WITH THE PACK CLOSE", "WITHOUT HESITATION",
            "AS THE GAP OPENS", "BEFORE THE NEXT CORNER",
            "WHILE THE PRESSURE BUILDS", "WITH EVERYTHING MOVING",
        )
        contexts = (
            "", "RIGHT NOW", "ON THIS LAP", "IN THIS SECTOR",
            "WITH RED COMMITTED", "AS THE FIELD CLOSES",
            "BEFORE IT SHUTS", "WITH NO EASY EXIT",
            "AND THE FIGHT CONTINUES", "WITH THE NEXT MOVE COMING",
            "AS THE ROAD TIGHTENS", "WHILE THE PACK RESPONDS",
        )

        start = self.counter + self.episode * 17
        total = len(pool) * len(modifiers) * len(contexts)
        stride = 1543  # coprime with the current grammar dimensions
        for offset in range(total):
            idx = (start + offset * stride) % total
            anchor = pool[idx % len(pool)]
            modifier = modifiers[(idx // len(pool)) % len(modifiers)]
            context = contexts[
                (idx // (len(pool) * len(modifiers))) % len(contexts)
            ]
            text = f"{anchor} — {modifier}" + (f" {context}" if context else "")
            if self._available(text):
                self.reserve(text)
                self.counter += offset + 1
                return text

        # Absolute safety valve: still preserve the event semantics by keeping
        # the original candidate as the anchor. Episode/moment identity is used
        # only after thousands of same-category variations have been exhausted.
        moment = self.counter + 1
        anchor = pool[(self.episode + moment) % len(pool)]
        text = f"{anchor} — RACE {self.episode} / MOMENT {moment}"
        while not self._available(text):
            moment += 1
            anchor = pool[(self.episode + moment) % len(pool)]
            text = f"{anchor} — RACE {self.episode} / MOMENT {moment}"
        self.reserve(text)
        self.counter = moment
        return text
