"""FastAPI application factory for the betTube Studio API server."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# Ensure repo root is on sys.path so `core.*` imports resolve when running
# the server from the repo root (e.g. `uvicorn server.app:app`).
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.runtime import load_repo_env

load_repo_env()

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routers import bootstrap, footage, jobs, media, plans, projects, scenes, settings, short_form, style_refs


def _frontend_dist_dir() -> Path:
    configured = str(os.getenv("BETTUBE_STUDIO_FRONTEND_DIST") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(_REPO_ROOT) / "frontend" / "dist").resolve()


def _path_is_inside(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _mount_frontend(application: FastAPI) -> None:
    """Serve the built React app when a Docker/production build is present."""
    dist_dir = _frontend_dist_dir()
    index_path = dist_dir / "index.html"
    if not index_path.exists():
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        application.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @application.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse | JSONResponse:
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={"message": "Unknown betTube Studio API route."},
            )

        candidate = (dist_dir / full_path).resolve()
        if full_path and _path_is_inside(candidate, dist_dir) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_path)


def create_app() -> FastAPI:
    application = FastAPI(title="betTube Studio API", version="0.1.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:9322",
            "http://localhost:9323",
            "http://127.0.0.1:9322",
            "http://127.0.0.1:9323",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(bootstrap.router, prefix="/api")
    application.include_router(projects.router, prefix="/api")
    application.include_router(plans.router, prefix="/api")
    application.include_router(scenes.router, prefix="/api")
    application.include_router(media.router, prefix="/api")
    application.include_router(jobs.router, prefix="/api")
    application.include_router(footage.router, prefix="/api")
    application.include_router(style_refs.router, prefix="/api")
    application.include_router(short_form.router, prefix="/api")
    application.include_router(settings.router, prefix="/api")

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "message": "betTube Studio API failed before it could finish the request.",
                "operatorHint": f"Inspect the failing route boundary and the provider call behind {exc.__class__.__name__}.",
            },
        )

    _mount_frontend(application)

    return application


app = create_app()
