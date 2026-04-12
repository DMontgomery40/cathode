"""Static media serving for project assets."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.runtime import PROJECTS_DIR, REPO_ROOT

router = APIRouter()

# Map extensions to MIME types for common media files
_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".json": "application/json",
    ".txt": "text/plain",
}


@router.get("/template-deck/{path:path}")
async def serve_template_deck(path: str) -> FileResponse:
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    deck_dir = REPO_ROOT / "template_deck"
    file_path = (deck_dir / path).resolve()

    if not str(file_path).startswith(str(deck_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    ext = file_path.suffix.lower()
    media_type = _MIME_MAP.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )


@router.get("/projects/{project}/media/{path:path}")
async def serve_media(project: str, path: str) -> FileResponse:
    # Security: reject path traversal
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    project_dir = PROJECTS_DIR / project
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project}")

    file_path = (project_dir / path).resolve()

    # Ensure resolved path is still inside the project directory
    if not str(file_path).startswith(str(project_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    ext = file_path.suffix.lower()
    media_type = _MIME_MAP.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )
