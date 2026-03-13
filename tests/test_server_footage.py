"""Integration tests for project-level footage uploads."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.app import create_app


@pytest.fixture()
def client():
    return TestClient(create_app())


def _plan():
    return {
        "meta": {
            "project_name": "demo",
            "brief": {
                "source_material": "Hello",
                "footage_manifest": [],
                "available_footage": "",
            },
        },
        "scenes": [],
    }


def test_upload_footage_appends_manifest_and_summary(client, tmp_path):
    (tmp_path / "demo").mkdir()
    saved = []

    with (
        patch("server.routers.footage.PROJECTS_DIR", tmp_path),
        patch("server.routers.footage.load_plan", return_value=_plan()),
        patch("server.routers.footage.save_plan", side_effect=lambda d, plan: saved.append(plan) or plan),
    ):
        resp = client.post(
            "/api/projects/demo/footage",
            files=[
                ("files", ("clip.mp4", b"fake-video-bytes", "video/mp4")),
                ("files", ("still.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png")),
            ],
        )

    assert resp.status_code == 200
    brief = saved[0]["meta"]["brief"]
    manifest = brief["footage_manifest"]
    assert len(manifest) == 2
    assert {item["kind"] for item in manifest} == {"video_clip", "image_still"}
    assert "clip" in brief["available_footage"].lower()


def test_upload_footage_rejects_unsupported_types(client, tmp_path):
    (tmp_path / "demo").mkdir()

    with (
        patch("server.routers.footage.PROJECTS_DIR", tmp_path),
        patch("server.routers.footage.load_plan", return_value=_plan()),
    ):
        resp = client.post(
            "/api/projects/demo/footage",
            files=[("files", ("notes.txt", b"hello", "text/plain"))],
        )

    assert resp.status_code == 415
