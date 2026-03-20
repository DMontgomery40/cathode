"""FastAPI application factory for the Cathode API server."""

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
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from server.routers import bootstrap, footage, jobs, media, plans, projects, scenes, settings, style_refs


def create_app() -> FastAPI:
    application = FastAPI(title="Cathode API", version="0.1.0")

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
                "message": "Cathode API failed before it could finish the request.",
                "operatorHint": f"Inspect the failing route boundary and the provider call behind {exc.__class__.__name__}.",
            },
        )

    return application


app = create_app()
