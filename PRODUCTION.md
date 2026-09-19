# GRIDLOOP production

The repository runs as a deterministic procedural racing show rather than a one-off renderer.

## Runtime

1. `career_state.json` stores continuity, rivals, unlocks and the next episode number.
2. `showrunner.py` creates a deterministic `episode_plan.json`.
3. `story_beats.py` supplies reusable story structures.
4. `track_system.py` selects an unlocked road and variant.
5. `race_engine.py` executes the plan physically.
6. `renderer_hybrid.py` combines the Python renderer with the native C++ map engine.
7. `audio.py` renders adaptive music and effects.
8. `quality_control.py` checks the finished Short. A failed episode rerenders with another deterministic seed, up to `MAX_RENDER_ATTEMPTS`.
9. `metadata.py` writes story-aware YouTube metadata.
10. `youtube_upload.py` uploads the accepted episode.
11. Only after YouTube returns a video id does `career.py` advance career state.

## Primary production: Railway

`gridloop_service.py` is the production scheduler and Ghost OS control target. The included `Dockerfile` installs FFmpeg, fonts and g++, compiles `cpp/map_engine.cpp`, and starts the worker.

Attach a Railway volume and configure:

- `GRIDLOOP_AGENT_KEY` — 32+ character control secret.
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `YOUTUBE_UPLOAD_ENABLED=true`
- `YOUTUBE_PRIVACY_STATUS=public`

Optional but recommended:

- `GRIDLOOP_GITHUB_TOKEN` — fine-grained token for **pseudodev3/youtube** with Contents read/write. After a successful upload the worker backs up `career_state.json` to the repository. This does not use GitHub Actions minutes.

The worker defaults to **09:17 and 21:17 WAT**. It starts paused on a fresh volume. Resume it from the GRIDLOOP card in Ghost OS after confirming the credentials.

Persistent state lives on the Railway volume. If the worker restarts after YouTube accepts an upload but before career advancement finishes, `upload_receipt.json` allows the next process to finish the career transaction without deliberately uploading the episode again.

## Safe behavior

- QC failure: no upload and no career advance.
- YouTube failure: no career advance.
- Successful upload: persistent career state advances only after a non-empty YouTube video id.
- Duplicate schedule protection: each morning/evening slot is attempted once automatically.
- Worker restart: the latest missed slot is eligible after the service returns.
- Manual **Render now**: available through Ghost OS and rejected while another render is active.
- GitHub backup failure: the uploaded career remains safe on the Railway volume; repo sync failure is reported separately.

## GitHub Actions fallback

`.github/workflows/render.yml` is now **manual-only**. It remains available as an emergency fallback when Actions minutes are available, but it is no longer the production scheduler. Normal production should run through Railway.
