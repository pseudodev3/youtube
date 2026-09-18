from __future__ import annotations


ROAD_CATALOG = {
    "training": {
        "threshold": 0.00,
        "theme": "training",
        "display": "Training Circuit",
        "variants": ["Open Sweepers", "Rookie Chicanes", "Hairpin School"],
        "curve_scale": 0.78,
        "section_len": 3.55,
        "width_scale": 1.05,
        "music_tension": 0.72,
    },
    "country": {
        "threshold": 0.28,
        "theme": "country",
        "display": "Country Roads",
        "variants": ["Farm Run", "Rolling Hills", "Village Sprint"],
        "curve_scale": 0.70,
        "section_len": 4.10,
        "width_scale": 1.03,
        "music_tension": 0.78,
    },
    "mountain": {
        "threshold": 0.42,
        "theme": "mountain",
        "display": "Mountain Pass",
        "variants": ["Cliff Hairpins", "Downhill S-Bends", "Summit Run"],
        "curve_scale": 1.15,
        "section_len": 2.55,
        "width_scale": 0.90,
        "music_tension": 0.86,
    },
    "night_city": {
        "threshold": 0.56,
        "theme": "night_city",
        "display": "Night City",
        "variants": ["Neon Boulevard", "Midnight Ring", "Downtown Sprint"],
        "curve_scale": 1.08,
        "section_len": 2.60,
        "width_scale": 0.88,
        "music_tension": 0.90,
    },
    "rain": {
        "threshold": 0.68,
        "theme": "rain",
        "display": "Wet Circuit",
        "variants": ["Storm Sprint", "Wet Switchbacks", "Standing Water"],
        "curve_scale": 1.12,
        "section_len": 2.65,
        "width_scale": 0.92,
        "music_tension": 0.94,
    },
    "coast": {
        "threshold": 0.72,
        "theme": "coast",
        "display": "Coastal Road",
        "variants": ["Ocean Cliffs", "Harbour Run", "Sunset Coast"],
        "curve_scale": 0.88,
        "section_len": 3.35,
        "width_scale": 0.95,
        "music_tension": 0.92,
    },
    "snow": {
        "threshold": 0.78,
        "theme": "snow",
        "display": "Snow Pass",
        "variants": ["Frozen Pines", "Whiteout Ridge", "Ice Hairpins"],
        "curve_scale": 1.00,
        "section_len": 3.05,
        "width_scale": 0.96,
        "music_tension": 0.98,
    },
    "canyon": {
        "threshold": 0.84,
        "theme": "canyon",
        "display": "Canyon Run",
        "variants": ["Red Rock Drop", "Knife Edge", "Canyon Switchbacks"],
        "curve_scale": 1.20,
        "section_len": 2.35,
        "width_scale": 0.84,
        "music_tension": 1.02,
    },
    "desert": {
        "threshold": 0.87,
        "theme": "desert",
        "display": "Desert Highway",
        "variants": ["Heat Mirage", "Dust Run", "Long Bend"],
        "curve_scale": 0.74,
        "section_len": 4.30,
        "width_scale": 1.00,
        "music_tension": 0.96,
    },
    "forest": {
        "threshold": 0.89,
        "theme": "forest",
        "display": "Forest Sprint",
        "variants": ["Pine Tunnel", "River Bend", "Dark Woods"],
        "curve_scale": 1.14,
        "section_len": 2.45,
        "width_scale": 0.85,
        "music_tension": 1.00,
    },
    "street": {
        "threshold": 0.91,
        "theme": "street",
        "display": "Street Circuit",
        "variants": ["Harbour Walls", "Old Town", "Concrete Maze"],
        "curve_scale": 1.24,
        "section_len": 2.15,
        "width_scale": 0.80,
        "music_tension": 1.06,
    },
    "tunnel": {
        "threshold": 0.93,
        "theme": "tunnel",
        "display": "Tunnel City",
        "variants": ["Underpass Rush", "Metro Loop", "Blackout Tunnel"],
        "curve_scale": 1.02,
        "section_len": 2.55,
        "width_scale": 0.82,
        "music_tension": 1.08,
    },
    "neon_rain": {
        "threshold": 0.945,
        "theme": "neon_rain",
        "display": "Neon Rain",
        "variants": ["Electric Storm", "Wet Neon Ring", "Midnight Flood"],
        "curve_scale": 1.20,
        "section_len": 2.20,
        "width_scale": 0.80,
        "music_tension": 1.12,
    },
    "alpine": {
        "threshold": 0.96,
        "theme": "alpine",
        "display": "Alpine Pass",
        "variants": ["Cloud Line", "Frozen Summit", "Alpine Descent"],
        "curve_scale": 1.25,
        "section_len": 2.10,
        "width_scale": 0.78,
        "music_tension": 1.15,
    },
    "extreme_canyon": {
        "threshold": 0.975,
        "theme": "extreme_canyon",
        "display": "Extreme Canyon",
        "variants": ["No-Margin Run", "The Drop", "Final Switchbacks"],
        "curve_scale": 1.32,
        "section_len": 1.95,
        "width_scale": 0.74,
        "music_tension": 1.20,
    },
}


VISUAL_FAMILY = {
    "training": "circuit",
    "country": "rural",
    "mountain": "mountains",
    "night_city": "urban",
    "rain": "circuit",
    "coast": "coast",
    "snow": "mountains",
    "canyon": "canyon",
    "desert": "desert",
    "forest": "forest",
    "street": "urban",
    "tunnel": "enclosed",
    "neon_rain": "urban",
    "alpine": "mountains",
    "extreme_canyon": "canyon",
}


def unlocked_roads(skill: float) -> list[str]:
    return [key for key, cfg in ROAD_CATALOG.items() if skill >= float(cfg["threshold"])]


def choose_track(career: dict, rng) -> dict:
    skill = float(career.get("driver_skill", 0.2))
    unlocked = unlocked_roads(skill)
    last_track = career.get("last_track")

    history = [
        str(entry.get("track"))
        for entry in career.get("history", [])[-2:]
        if entry.get("track") in ROAD_CATALOG
    ]
    recent_tracks = set(history)
    recent_families = {VISUAL_FAMILY.get(key, key) for key in history}
    same_recent_family = len(history) >= 2 and len(recent_families) == 1

    # Prefer a different-looking world, not merely a different track id.
    # This remains probabilistic: continuity is preserved, but visual repetition
    # becomes increasingly unlikely when distinct unlocked environments exist.
    weights: list[float] = []
    newest = unlocked[-1] if unlocked else "training"
    for idx, key in enumerate(unlocked):
        family = VISUAL_FAMILY.get(key, key)
        weight = 1.0 + idx * 0.22

        # Recently unlocked roads deserve discovery time.
        if key == newest and len(unlocked) > 1:
            weight *= 1.35

        # Never hard-ban repeats, but make back-to-back reuse genuinely rare.
        if key == last_track and len(unlocked) > 1:
            weight *= 0.04
        elif key in recent_tracks and len(unlocked) > 2:
            weight *= 0.28

        # Prefer a fresh visual family. If the last two races looked alike,
        # amplify the pressure to move to a different kind of environment.
        if recent_families and family not in recent_families:
            weight *= 2.35 if same_recent_family else 1.65
        elif family in recent_families and len({VISUAL_FAMILY.get(k, k) for k in unlocked}) > 1:
            weight *= 0.72

        weights.append(max(0.001, weight))

    if unlocked:
        key = rng.choices(unlocked, weights=weights, k=1)[0]
    else:
        key = "training"

    cfg = ROAD_CATALOG[key]
    variant = rng.choice(cfg["variants"])
    return {
        "key": key,
        "theme": cfg["theme"],
        "name": f"{cfg['display']} — {variant}",
        "variant": variant,
        "curve_scale": float(cfg["curve_scale"]),
        "section_len": float(cfg["section_len"]),
        "width_scale": float(cfg["width_scale"]),
        "music_tension": float(cfg["music_tension"]),
        "difficulty": round(min(1.0, 0.30 + skill * 0.70), 3),
    }
