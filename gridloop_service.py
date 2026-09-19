from __future__ import annotations

import base64
import hmac
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_mount = os.getenv("GRIDLOOP_DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
DATA_DIR = Path(_mount).expanduser().resolve() / ("gridloop" if _mount and Path(_mount).name != "gridloop" else "") if _mount else ROOT / ".gridloop-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CAREER_PATH = DATA_DIR / "career_state.json"
OUTPUT_DIR = DATA_DIR / "output"
STATE_PATH = DATA_DIR / "service_state.json"
SEED_CAREER = ROOT / "career_state.json"
FRESH_STATE = not STATE_PATH.exists()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AGENT_KEY = os.getenv("GRIDLOOP_AGENT_KEY", "").strip()
PORT = int(os.getenv("PORT", "3000"))
TZ_OFFSET = int(os.getenv("GRIDLOOP_TZ_OFFSET_MINUTES", "60"))
LOCAL_TZ = timezone(timedelta(minutes=TZ_OFFSET))
MORNING = os.getenv("GRIDLOOP_MORNING", "09:17")
EVENING = os.getenv("GRIDLOOP_EVENING", "21:17")
GITHUB_TOKEN = os.getenv("GRIDLOOP_GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GRIDLOOP_GITHUB_REPO", "pseudodev3/youtube").strip()
GITHUB_BRANCH = os.getenv("GRIDLOOP_GITHUB_BRANCH", "main").strip() or "main"

if len(AGENT_KEY) < 32:
    raise RuntimeError("GRIDLOOP_AGENT_KEY must contain at least 32 characters")


def _clock(value: str) -> tuple[int, int]:
    try:
        hour, minute = [int(x) for x in value.split(":", 1)]
    except Exception as exc:
        raise RuntimeError(f"Invalid schedule time: {value!r}") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise RuntimeError(f"Invalid schedule time: {value!r}")
    return hour, minute


MORNING_HM = _clock(MORNING)
EVENING_HM = _clock(EVENING)

DEFAULT_STATE = {
    "paused": True,
    "lastAttemptedSlot": None,
    "lastCompletedSlot": None,
    "lastStarted": None,
    "lastFinished": None,
    "lastStatus": "idle",
    "lastVideoId": None,
    "lastTitle": None,
    "lastTrack": None,
    "lastError": None,
    "lastRepoSync": None,
    "logs": [],
}

state_lock = threading.RLock()
job_lock = threading.Lock()
stop_event = threading.Event()
current_process: subprocess.Popen[str] | None = None


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(temp, path)


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return dict(DEFAULT_STATE)
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_STATE)
    out = dict(DEFAULT_STATE)
    if isinstance(raw, dict):
        out.update(raw)
    out["paused"] = bool(out.get("paused", True))
    out["logs"] = list(out.get("logs", []))[-120:]
    return out


STATE = _load_state()


def _save_state() -> None:
    with state_lock:
        _atomic_json(STATE_PATH, STATE)


def log(message: str) -> None:
    line = str(message).replace("\r", " ").strip()
    if not line:
        return
    stamp = datetime.now(timezone.utc).isoformat()
    with state_lock:
        STATE["logs"] = (list(STATE.get("logs", [])) + [{"at": stamp, "message": line[:600]}])[-120:]
    print(line, flush=True)


def _seed_career() -> None:
    if CAREER_PATH.exists():
        return
    if not SEED_CAREER.exists():
        raise RuntimeError("Repository career_state.json is missing")
    shutil.copy2(SEED_CAREER, CAREER_PATH)
    log(f"Seeded persistent career from repository at episode {_career_episode()}.")


def _career() -> dict:
    try:
        return json.loads(CAREER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _career_episode() -> int:
    try:
        return int(_career().get("episode", 1))
    except Exception:
        return 1


def _upload_configured() -> bool:
    enabled = os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").strip().lower() == "true"
    return enabled and all(os.getenv(name, "").strip() for name in (
        "YOUTUBE_CLIENT_ID",
        "YOUTUBE_CLIENT_SECRET",
        "YOUTUBE_REFRESH_TOKEN",
    ))


def _slot_dt(day, hm: tuple[int, int]) -> datetime:
    return datetime(day.year, day.month, day.day, hm[0], hm[1], tzinfo=LOCAL_TZ)


def latest_slot(now: datetime | None = None) -> tuple[str, datetime]:
    now = (now or datetime.now(timezone.utc)).astimezone(LOCAL_TZ)
    morning = _slot_dt(now.date(), MORNING_HM)
    evening = _slot_dt(now.date(), EVENING_HM)
    if now >= evening:
        return f"{now.date().isoformat()}-evening", evening
    if now >= morning:
        return f"{now.date().isoformat()}-morning", morning
    prev = now.date() - timedelta(days=1)
    dt = _slot_dt(prev, EVENING_HM)
    return f"{prev.isoformat()}-evening", dt


def next_slot(now: datetime | None = None) -> tuple[str, datetime]:
    now = (now or datetime.now(timezone.utc)).astimezone(LOCAL_TZ)
    morning = _slot_dt(now.date(), MORNING_HM)
    evening = _slot_dt(now.date(), EVENING_HM)
    if now < morning:
        return f"{now.date().isoformat()}-morning", morning
    if now < evening:
        return f"{now.date().isoformat()}-evening", evening
    nxt = now.date() + timedelta(days=1)
    dt = _slot_dt(nxt, MORNING_HM)
    return f"{nxt.isoformat()}-morning", dt


def _github_request(url: str, *, method: str = "GET", body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gridloop-railway-worker",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def sync_career_to_github() -> bool | None:
    if not GITHUB_TOKEN:
        return None
    try:
        api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/career_state.json"
        current = _github_request(api + f"?ref={GITHUB_BRANCH}")
        body = {
            "message": "Advance GRIDLOOP career from Railway [skip ci]",
            "content": base64.b64encode(CAREER_PATH.read_bytes()).decode("ascii"),
            "sha": current["sha"],
            "branch": GITHUB_BRANCH,
        }
        _github_request(api, method="PUT", body=body)
        log("Synced career_state.json back to GitHub.")
        return True
    except Exception as exc:
        log(f"GitHub career sync failed: {exc}")
        return False


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _prune_output() -> None:
    videos = sorted(OUTPUT_DIR.glob("episode_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in videos[2:]:
        path.unlink(missing_ok=True)
    for path in OUTPUT_DIR.glob("*.video.mp4"):
        path.unlink(missing_ok=True)
    for path in OUTPUT_DIR.glob("*.wav"):
        path.unlink(missing_ok=True)


def _finish_job(slot_id: str, trigger: str, code: int) -> None:
    run_status = _read_json(OUTPUT_DIR / "run_status.json")
    metadata = _read_json(OUTPUT_DIR / "metadata.json")
    success = code == 0 and run_status.get("status") in {"uploaded", "uploaded_recovered"}

    # Persist the completed slot before any optional external backup. If a GitHub
    # backup commit causes Railway to redeploy, the restarted worker still knows
    # this slot is finished and will not upload it again.
    with state_lock:
        STATE["lastFinished"] = datetime.now(timezone.utc).isoformat()
        STATE["lastStatus"] = "uploaded" if success else "failed"
        STATE["lastError"] = None if success else (
            run_status.get("reason")
            or run_status.get("status")
            or f"renderer exited with code {code}"
        )
        if success:
            STATE["lastVideoId"] = run_status.get("video_id")
            STATE["lastTitle"] = run_status.get("title") or metadata.get("title")
            STATE["lastTrack"] = run_status.get("track") or metadata.get("track")
            if not slot_id.startswith("manual:"):
                STATE["lastCompletedSlot"] = slot_id
    _save_state()

    repo_sync = sync_career_to_github() if success else None
    with state_lock:
        STATE["lastRepoSync"] = repo_sync
    _save_state()
    _prune_output()

    if success:
        log(
            f"GRIDLOOP upload complete for {slot_id}: "
            f"https://youtu.be/{STATE.get('lastVideoId')}"
        )
    else:
        log(f"GRIDLOOP job failed for {slot_id}. {STATE.get('lastError')}")


def _run_job(slot_id: str, trigger: str) -> None:
    global current_process
    try:
        for stale in ("run_status.json", "metadata.json", "qc.json", "telemetry.json"):
            (OUTPUT_DIR / stale).unlink(missing_ok=True)

        env = os.environ.copy()
        env.update({
            "CAREER_PATH": str(CAREER_PATH),
            "GRIDLOOP_OUTPUT_DIR": str(OUTPUT_DIR),
            "GITHUB_EVENT_NAME": "gridloop_service",
        })

        log(f"Starting GRIDLOOP episode {_career_episode()} ({trigger}, slot {slot_id}).")
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        current_process = proc
        if proc.stdout:
            for line in proc.stdout:
                text = line.strip()
                if text and (
                    "QC attempt" in text
                    or "Uploaded episode" in text
                    or "Career advanced" in text
                    or "GRIDLOOP map engine" in text
                    or "Recovered uploaded" in text
                    or "Traceback" in text
                    or "Error" in text
                    or "RuntimeError" in text
                ):
                    log(text)
        code = proc.wait()
        _finish_job(slot_id, trigger, code)
    except Exception as exc:
        with state_lock:
            STATE["lastFinished"] = datetime.now(timezone.utc).isoformat()
            STATE["lastStatus"] = "failed"
            STATE["lastError"] = str(exc)[:800]
        _save_state()
        log(f"GRIDLOOP worker exception: {exc}")
    finally:
        current_process = None
        job_lock.release()


def start_job(slot_id: str, trigger: str) -> tuple[bool, str]:
    if not _upload_configured():
        return False, "YouTube upload is not configured on the GRIDLOOP Railway service."
    if not job_lock.acquire(blocking=False):
        return False, "A GRIDLOOP render is already in progress."

    with state_lock:
        STATE["lastAttemptedSlot"] = slot_id
        STATE["lastStarted"] = datetime.now(timezone.utc).isoformat()
        STATE["lastStatus"] = "rendering"
        STATE["lastError"] = None
    _save_state()
    threading.Thread(target=_run_job, args=(slot_id, trigger), daemon=True).start()
    return True, f"Started episode {_career_episode()}."


def _schedule_tick() -> None:
    if stop_event.is_set():
        return
    with state_lock:
        paused = bool(STATE.get("paused", True))
        attempted = STATE.get("lastAttemptedSlot")
        completed = STATE.get("lastCompletedSlot")
    if paused or not _upload_configured() or job_lock.locked():
        return
    slot_id, _ = latest_slot()
    if attempted == slot_id or completed == slot_id:
        return
    start_job(slot_id, "schedule")


def scheduler_loop() -> None:
    while not stop_event.wait(20):
        try:
            _schedule_tick()
        except Exception as exc:
            log(f"Scheduler check failed: {exc}")


def status_payload() -> dict:
    nxt_id, nxt_dt = next_slot()
    current = _career()
    with state_lock:
        payload = {
            "ok": True,
            "configured": _upload_configured(),
            "paused": bool(STATE.get("paused", True)),
            "inFlight": job_lock.locked(),
            "episode": int(current.get("episode", 1) or 1),
            "driverSkill": current.get("driver_skill"),
            "unlockedRoads": current.get("unlocked_roads", []),
            "lastAttemptedSlot": STATE.get("lastAttemptedSlot"),
            "lastCompletedSlot": STATE.get("lastCompletedSlot"),
            "lastStarted": STATE.get("lastStarted"),
            "lastFinished": STATE.get("lastFinished"),
            "lastStatus": STATE.get("lastStatus"),
            "lastVideoId": STATE.get("lastVideoId") or current.get("last_video_id"),
            "lastTitle": STATE.get("lastTitle") or current.get("last_title"),
            "lastTrack": STATE.get("lastTrack") or current.get("last_track"),
            "lastError": STATE.get("lastError"),
            "nextSlot": nxt_id,
            "nextSlotAt": nxt_dt.astimezone(timezone.utc).isoformat(),
            "timezoneOffsetMinutes": TZ_OFFSET,
            "repoSyncConfigured": bool(GITHUB_TOKEN),
            "lastRepoSync": STATE.get("lastRepoSync"),
            "persistence": str(DATA_DIR),
            "logs": list(STATE.get("logs", []))[-30:],
        }
    return payload


class Handler(BaseHTTPRequestHandler):
    server_version = "GRIDLOOP/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, "Bearer " + AGENT_KEY)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return self._json(200, {
                "ok": True,
                "configured": _upload_configured(),
                "inFlight": job_lock.locked(),
            })
        if not self._authorized():
            return self._json(401, {"error": "Unauthorized"})
        if path == "/status":
            return self._json(200, status_payload())
        return self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if not self._authorized():
            return self._json(401, {"error": "Unauthorized"})
        if path != "/command":
            return self._json(404, {"error": "Not found"})
        try:
            size = int(self.headers.get("Content-Length", "0") or 0)
            if size <= 0 or size > 2048:
                raise ValueError("Invalid request size")
            body = json.loads(self.rfile.read(size).decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "Invalid request"})

        action = body.get("action")
        if action == "pause":
            with state_lock:
                STATE["paused"] = True
            _save_state()
            log("GRIDLOOP schedule paused.")
            return self._json(200, {"ok": True, "paused": True})
        if action == "resume":
            with state_lock:
                STATE["paused"] = False
            _save_state()
            log("GRIDLOOP schedule resumed.")
            _schedule_tick()
            return self._json(200, {"ok": True, "paused": False})
        if action == "render":
            current_slot, _ = latest_slot()
            with state_lock:
                completed = STATE.get("lastCompletedSlot")
            slot_id = current_slot if completed != current_slot else "manual:" + datetime.now(timezone.utc).isoformat()
            ok, message = start_job(slot_id, "manual")
            return self._json(202 if ok else 409, {"ok": ok, "message": message, "slot": slot_id})
        return self._json(400, {"error": "Unknown action"})


def shutdown(*_args) -> None:
    stop_event.set()
    proc = current_process
    if proc and proc.poll() is None:
        log("Shutdown requested; terminating active renderer.")
        proc.terminate()


def main() -> None:
    _seed_career()
    if FRESH_STATE and int(_career().get("uploads", 0) or 0) > 0:
        # Migration safety: existing episodes were produced elsewhere before this
        # Railway scheduler existed. Treat the current slot as already handled so
        # first-time Resume cannot immediately create a duplicate. Use Render now
        # explicitly if the current slot really was missed.
        slot_id, _ = latest_slot()
        with state_lock:
            STATE["lastAttemptedSlot"] = slot_id
            STATE["lastCompletedSlot"] = slot_id
        log(f"Migration baseline set at {slot_id}; next automatic run is the following slot.")
    _save_state()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log(
        f"GRIDLOOP Railway worker ready on port {PORT}. "
        f"Schedule {MORNING}/{EVENING} UTC{TZ_OFFSET / 60:+g}; "
        f"{'paused' if STATE.get('paused') else 'running'}."
    )
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        stop_event.set()
        server.server_close()


if __name__ == "__main__":
    main()
