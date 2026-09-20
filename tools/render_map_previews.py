from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# These must be set before importing main.py because its render constants are
# resolved at import time.
os.environ.setdefault("FPS", "24")
os.environ.setdefault("DURATION", "8")
os.environ["YOUTUBE_UPLOAD_ENABLED"] = "false"
os.environ.setdefault("GRIDLOOP_OUTPUT_DIR", "output/map-previews")

from career import load_career
from main import render_video
from showrunner import plan_episode
from track_system import ROAD_CATALOG

TRACKS = ("training", "country", "mountain", "canyon", "night_city", "coast", "forest", "desert")
OUT = Path(os.environ["GRIDLOOP_OUTPUT_DIR"])
OUT.mkdir(parents=True, exist_ok=True)


def forced_track(key: str) -> dict:
    cfg = ROAD_CATALOG[key]
    variant = cfg["variants"][0]
    return {
        "key": key,
        "theme": cfg["theme"],
        "name": f"{cfg['display']} — {variant}",
        "variant": variant,
        "curve_scale": float(cfg["curve_scale"]),
        "section_len": float(cfg["section_len"]),
        "width_scale": float(cfg["width_scale"]),
        "music_tension": float(cfg["music_tension"]),
        "difficulty": 0.75,
    }


def main() -> None:
    career = load_career()
    # One deterministic race plan for every world. Only the map changes.
    base = plan_episode(career, attempt=0, duration=float(os.environ["DURATION"])).to_dict()
    manifest = []

    for key in TRACKS:
        plan = json.loads(json.dumps(base))
        plan["track"] = forced_track(key)
        plan["objective_text"] = f"MAP PREVIEW • {key.upper()}"

        rendered, telemetry = render_video(career, plan)
        destination = OUT / f"{key}.mp4"
        if destination.exists():
            destination.unlink()
        shutil.move(str(rendered), destination)

        # Grab a representative frame from the same full renderer for quick visual review.
        still = OUT / f"{key}.jpg"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-ss", "4", "-i", str(destination),
                "-frames:v", "1", "-q:v", "2", str(still),
            ],
            check=True,
        )

        manifest.append({
            "track": key,
            "video": destination.name,
            "still": still.name,
            "story_type": plan.get("story_type"),
            "featured_rival": plan.get("featured_rival"),
            "events": telemetry.get("event_count"),
            "final_position": telemetry.get("final_position"),
        })
        print(f"MAP PREVIEW complete: {key} -> {destination}")

    # One phone-sized 2x2 sheet makes "do these feel like different worlds?"
    # immediately reviewable without scrubbing four videos.
    rows = (len(TRACKS) + 1) // 2
    sheet = Image.new("RGB", (1080, rows * 960), (18, 20, 21))
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    font = ImageFont.truetype(str(font_path), 28) if font_path.exists() else ImageFont.load_default()
    for index, key in enumerate(TRACKS):
        still = Image.open(OUT / f"{key}.jpg").convert("RGB").resize((540, 960), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(still)
        draw.rounded_rectangle([18, 18, 230, 64], radius=12, fill=(10, 12, 13))
        draw.text((32, 27), key.upper(), font=font, fill=(244, 245, 242))
        x = (index % 2) * 540
        y = (index // 2) * 960
        sheet.paste(still, (x, y))
    sheet.save(OUT / "comparison.jpg", quality=92)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
