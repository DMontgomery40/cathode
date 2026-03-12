from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_generate_project_assets_helper_requests_video_generation():
    script = (REPO_ROOT / "generate_project_assets.sh").read_text()

    assert "generate_project_assets_service(" in script
    assert "generate_videos=True" in script
