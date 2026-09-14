# GRIDLOOP production

The repository now runs as a deterministic procedural racing show rather than a one-off renderer.

## Runtime

1. `career_state.json` stores continuity, rivals, unlocks and the next episode number.
2. `showrunner.py` creates a deterministic `episode_plan.json`.
3. `story_beats.py` supplies reusable story structures.
4. `track_system.py` selects an unlocked road and variant.
5. `race_engine.py` executes the plan physically.
6. `renderer.py` and `audio.py` render the episode with adaptive music.
7. `quality_control.py` checks the finished Short. A failed episode rerenders with another deterministic seed, up to `MAX_RENDER_ATTEMPTS`.
8. `metadata.py` writes story-aware YouTube metadata.
9. `youtube_upload.py` uploads the accepted episode.
10. Only after YouTube returns a video id does `career.py` advance `career_state.json`.

## Required GitHub Actions secrets

Add these under **Repository Settings → Secrets and variables → Actions → New repository secret**:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

The workflow automatically treats the pipeline as preview-only until all three secrets exist. Manual runs still render artifacts. Scheduled runs remain dormant without credentials.

## Safe behavior

- QC failure: no upload, no career advance.
- YouTube failure: no career advance.
- Missing YouTube secrets: manual preview works, scheduled run skips.
- Successful upload: `career_state.json` advances and is committed with `[skip ci]`.

## Triggering a preview

Update `.github/run-now` or run the `GRIDLOOP production episode` workflow manually. The artifact contains the MP4, episode plan, telemetry, metadata, QC report and run status.

## Schedule

The production workflow currently runs daily at `08:17 UTC` once YouTube credentials are configured.
