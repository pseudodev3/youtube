from __future__ import annotations

import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload_enabled() -> bool:
    return os.getenv("YOUTUBE_UPLOAD_ENABLED", "false").strip().lower() == "true"


def _credentials() -> Credentials:
    client_id = os.environ["YOUTUBE_CLIENT_ID"]
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"]
    refresh_token = os.environ["YOUTUBE_REFRESH_TOKEN"]
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def upload_video(video_path: Path, metadata: dict) -> str:
    """Upload one finished episode and return the YouTube video id.

    Any exception bubbles up. The caller must never advance career state unless this
    function returns a non-empty id.
    """
    if not upload_enabled():
        raise RuntimeError("YouTube upload requested while YOUTUBE_UPLOAD_ENABLED is false")

    youtube = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata.get("tags", []),
            "categoryId": metadata.get("category_id", "20"),
        },
        "status": {
            "privacyStatus": metadata.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = str(response.get("id", "")).strip()
    if not video_id:
        raise RuntimeError(f"YouTube upload returned no video id: {response}")
    return video_id
