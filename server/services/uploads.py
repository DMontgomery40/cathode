"""Shared upload validation and persistence helpers for the FastAPI layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile


@dataclass(frozen=True)
class UploadSpec:
    label: str
    max_bytes: int
    allowed_extensions: tuple[str, ...]
    allowed_content_types: tuple[str, ...]


IMAGE_UPLOAD_SPEC = UploadSpec(
    label="image",
    max_bytes=64 * 1024 * 1024,
    allowed_extensions=(".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".heic", ".heif"),
    allowed_content_types=(
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/svg+xml",
        "image/heic",
        "image/heif",
    ),
)

STYLE_REF_UPLOAD_SPEC = UploadSpec(
    label="style reference",
    max_bytes=32 * 1024 * 1024,
    allowed_extensions=IMAGE_UPLOAD_SPEC.allowed_extensions,
    allowed_content_types=IMAGE_UPLOAD_SPEC.allowed_content_types,
)

VIDEO_UPLOAD_SPEC = UploadSpec(
    label="video",
    max_bytes=1024 * 1024 * 1024,
    allowed_extensions=(".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"),
    allowed_content_types=(
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/x-msvideo",
        "video/x-matroska",
    ),
)

_CONTENT_TYPE_TO_EXTENSION = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
}


def _normalized_content_type(upload: UploadFile) -> str:
    return (upload.content_type or "").split(";")[0].strip().lower()


def _resolve_upload_suffix(upload: UploadFile, spec: UploadSpec) -> str:
    suffix = Path(upload.filename or "").suffix.lower().strip()
    content_type = _normalized_content_type(upload)

    if suffix in spec.allowed_extensions:
        return suffix

    mapped = _CONTENT_TYPE_TO_EXTENSION.get(content_type)
    if mapped and mapped in spec.allowed_extensions:
        return mapped

    allowed = ", ".join(spec.allowed_extensions)
    raise HTTPException(
        status_code=415,
        detail=f"Unsupported {spec.label} type. Allowed file extensions: {allowed}.",
    )


def _validate_content_type(upload: UploadFile, spec: UploadSpec) -> None:
    content_type = _normalized_content_type(upload)
    if not content_type or content_type == "application/octet-stream":
        return
    if content_type not in spec.allowed_content_types:
        allowed = ", ".join(spec.allowed_content_types)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported {spec.label} content type '{content_type}'. Allowed types: {allowed}.",
        )


async def persist_upload(
    upload: UploadFile,
    *,
    dest_dir: Path,
    stem: str,
    spec: UploadSpec,
) -> Path:
    """Validate and persist an uploaded file without reading the full body into memory."""
    _validate_content_type(upload, spec)
    suffix = _resolve_upload_suffix(upload, spec)
    if upload.size is not None and upload.size > spec.max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{spec.label.capitalize()} upload exceeds the {spec.max_bytes // (1024 * 1024)} MB limit.",
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{stem}{suffix}"

    total = 0
    try:
        with dest.open("wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > spec.max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"{spec.label.capitalize()} upload exceeds the {spec.max_bytes // (1024 * 1024)} MB limit.",
                    )
                handle.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if total == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Uploaded {spec.label} file was empty.")

    return dest
