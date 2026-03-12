from __future__ import annotations

from core.demo_assets import normalize_footage_manifest


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
