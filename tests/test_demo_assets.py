from __future__ import annotations

from pathlib import Path

import core.demo_assets as demo_assets
from core.demo_assets import copy_footage_manifest_into_project, normalize_footage_manifest


def test_normalize_footage_manifest_falls_back_when_priority_is_not_numeric(tmp_path):
    clip_path = tmp_path / "demo.mp4"
    clip_path.write_bytes(b"clip")

    manifest = normalize_footage_manifest(
        [
            {
                "path": str(clip_path),
                "label": "Hero clip",
                "priority": "high",
            }
        ]
    )

    assert manifest[0]["priority"] == 1


def test_copy_footage_manifest_into_project_uses_streaming_copy(monkeypatch, tmp_path):
    source_clip = tmp_path / "source.mp4"
    source_clip.write_bytes(b"clip")
    project_dir = tmp_path / "project"
    copied_calls = []

    def fake_copy2(src, dest):
        copied_calls.append((Path(src), Path(dest)))
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(Path(src).read_bytes())
        return dest

    monkeypatch.setattr(demo_assets.shutil, "copy2", fake_copy2)

    copied = copy_footage_manifest_into_project(
        project_dir,
        [{"id": "hero", "path": str(source_clip), "label": "Hero clip"}],
    )

    assert copied_calls
    assert copied[0]["path"].endswith("clips/hero.mp4")
    assert Path(copied[0]["path"]).exists()
