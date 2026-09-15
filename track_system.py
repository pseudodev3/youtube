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
        # The original country palette matched Training almost exactly. Reuse the
        # darker rural/woodland renderer palette so this unlock reads immediately
        # as a new location while retaining Country's own road geometry/variants.
        "theme": "forest",
        "display": "Country Roads",
        "variants": ["Farm Run", "Rolling Hills", "Village Sprint"],
        "curve_scale": 0.90,
        "section_len": 3.30,
        "width_scale": 1.00,
        "music_tension": 0.78,
    },
    "mountain": {
        "threshold": 0.42,
        "theme": "mountain",
        "display": "Mountain Pass",
        "variants": ["Cliff Hairpins", "Downhill S-Bends", "Summit Run"],
        "curve_scale": 1.05,
        "section_len": 2.95,
        "width_scale": 0.94,
        "music_tension": 0.86,
    },
    "night_city": {
        "threshold": 0.56,
        "theme": "night_city",
        "display": "Night City",
        "variants": ["Neon Boulevard", "Midnight Ring", "Downtown Sprint"],
        "curve_scale": 1.00,
        "section_len": 2.90,
        "width_scale": 0.92,
        "music_tension": 0.90,
    },
    "rain": {
        "threshold": 0.68,
        "theme": "rain",
        "display": "Wet Circuit",
        "variants": ["Storm Sprint", "Wet Switchbacks", "Standing Water"],
        "curve_scale": 1.06,
        "section_len": 2.85,
        "width_scale": 0.93,
        "music_tension": 0.94,
    },
    "coast": {
        "threshold": 0.72,
        "theme": "coast",
        "display": "Coastal Road",
        "variants": ["Ocean Cliffs", "Harbour Run", "Sunset Coast"],
        "curve_scale": 1.02,
        "section_len": 2.80,
        "width_scale": 0.91,
        "music_tension": 0.92,
    },
    "snow": {
        "threshold": 0.78,
        "theme": "snow",
        "display": "Snow Pass",
        "variants": ["Frozen Pines", "Whiteout Ridge", "Ice Hairpins"],
        "curve_scale": 1.08,
        "section_len": 2.70,
        "width_scale": 0.90,
        "music_tension": 0.98,
    },
    "canyon": {
        "threshold": 0.84,
        "theme": "canyon",
        "display": "Canyon Run",
        "variants": ["Red Rock Drop", "Knife Edge", "Canyon Switchbacks"],
        "curve_scale": 1.12,
        "section_len": 2.62,
        "width_scale": 0.88,
        "music_tension": 1.02,
    },
    "desert": {
        "threshold": 0.87,
        "theme": "desert",
        "display": "Desert Highway",
        "variants": ["Heat Mirage", "Dust Run", "Long Bend"],
        "curve_scale": 0.98,
        "section_len": 2.85,
        "width_scale": 0.92,
        "music_tension": 0.96,
    },
    "forest": {
        "threshold": 0.89,
        "theme": "forest",
        "display": "Forest Sprint",
        "variants": ["Pine Tunnel", "River Bend", "Dark Woods"],
        "curve_scale": 1.10,
        "section_len": 2.58,
        "width_scale": 0.87,
        "music_tension": 1.00,
    },
    "street": {
        "threshold": 0.91,
        "theme": "street",
        "display": "Street Circuit",
        "variants": ["Harbour Walls", "Old Town", "Concrete Maze"],
        "curve_scale": 1.14,
        "section_len": 2.45,
        "width_scale": 0.84,
        "music_tension": 1.06,
    },
    "tunnel": {
        "threshold": 0.93,
        "theme": "tunnel",
        "display": "Tunnel City",
        "variants": ["Underpass Rush", "Metro Loop", "Blackout Tunnel"],
        "curve_scale": 1.08,
        "section_len": 2.48,
        "width_scale": 0.85,
        "music_tension": 1.08,
    },
    "neon_rain": {
        "threshold": 0.945,
        "theme": "neon_rain",
        "display": "Neon Rain",
        "variants": ["Electric Storm", "Wet Neon Ring", "Midnight Flood"],
        "curve_scale": 1.15,
        "section_len": 2.38,
        "width_scale": 0.83,
        "music_tension": 1.12,
    },
    "alpine": {
        "threshold": 0.96,
        "theme": "alpine",
        "display": "Alpine Pass",
        "variants": ["Cloud Line", "Frozen Summit", "Alpine Descent"],
        "curve_scale": 1.18,
        "section_len": 2.30,
        "width_scale": 0.82,
        "music_tension": 1.15,
    },
    "extreme_canyon": {
        "threshold": 0.975,
        "theme": "extreme_canyon",
        "display": "Extreme Canyon",
        "variants": ["No-Margin Run", "The Drop", "Final Switchbacks"],
        "curve_scale": 1.22,
        "section_len": 2.20,
        "width_scale": 0.80,
        "music_tension": 1.20,
    },
}


def unlocked_roads(skill: float) -> list[str]:
    return [key for key, cfg in ROAD_CATALOG.items() if skill >= float(cfg["threshold"])]


def choose_track(career: dict, rng) -> dict:
    skill = float(career.get("driver_skill", 0.2))
    unlocked = unlocked_roads(skill)
    last_track = career.get("last_track")

    # Bias toward recently unlocked/harder roads while still revisiting old locations.
    weighted: list[str] = []
    for idx, key in enumerate(unlocked):
        copies = 1 + idx // 3
        if key == last_track and len(unlocked) > 1:
            copies = max(1, copies - 1)
        weighted.extend([key] * copies)

    key = rng.choice(weighted or ["training"])
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
