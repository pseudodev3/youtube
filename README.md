# YouTube Racing Automation

A procedural vertical racing-video pipeline built with Python, Pillow and FFmpeg.

## What it does

- Simulates a driver that genuinely improves over time.
- Renders a polished 1080x1920 race with curved perspective roads, rivals, scenery, HUD and crash effects.
- Stores progression in `state.json` so every episode advances the driver.
- Unlocks harder road classes as skill increases.
- Encodes an H.264 MP4 with FFmpeg.
- Generates upload metadata in `output/metadata.json`.
- Runs automatically in GitHub Actions and uploads the rendered video as an artifact.

## Run locally

```bash
pip install -r requirements.txt
python main.py
```

FFmpeg must be installed and available in `PATH`.

## GitHub Actions

Open **Actions → Render racing short → Run workflow** to create a test episode immediately.

The current workflow also runs once daily. After a successful render it commits the updated `state.json` so the next video continues from the previous driver's skill level.

## Current progression

The driver begins intentionally rough. Skill affects reaction time, steering precision, corner anticipation, speed and crash probability.

Road milestones currently unlock in this order:

`training → country → mountain → night_city → rain → snow → canyon`

## Next phase

The first milestone is visual/gameplay validation. Once the race style is locked in, the pipeline can add custom sprite sheets, multiple environments, sound/music, richer events and authenticated YouTube Shorts uploading.
