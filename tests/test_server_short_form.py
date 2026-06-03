from unittest.mock import patch

from fastapi.testclient import TestClient

from server.app import create_app


def test_short_form_options_endpoint_returns_modes():
    client = TestClient(create_app())

    resp = client.get("/api/short-form/options")

    assert resp.status_code == 200
    body = resp.json()
    assert body["defaults"]["render_profile"]["aspect_ratio"] == "9:16"
    assert body["approaches"][0]["value"] == "public-reframe"


def test_preview_short_form_payload_returns_vertical_render_contract():
    client = TestClient(create_app())

    resp = client.post(
        "/api/short-form/preview",
        json={
            "project_name": "short_demo",
            "source_material": "Source notes",
            "hook_promise": "A fast proof moment",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["brief"]["short_form_format"] == "vertical_short"
    assert body["render_profile"]["aspect_ratio"] == "9:16"


@patch(
    "server.routers.short_form.create_make_video_job",
    return_value={
        "status": "queued",
        "job_id": "short-job-1",
        "project_name": "short_demo",
        "project_dir": "/tmp/short_demo",
        "kind": "make_video",
        "current_stage": "queued",
        "retryable": False,
        "suggestion": "",
        "requested_stage": "storyboard",
        "result": {},
        "error": None,
    },
)
def test_dispatch_short_form_job_calls_make_video_with_vertical_profile(mock_create):
    client = TestClient(create_app())

    resp = client.post(
        "/api/short-form/jobs",
        json={
            "project_name": "short_demo",
            "source_material": "Source notes",
            "run_until": "storyboard",
        },
    )

    assert resp.status_code == 200
    kwargs = mock_create.call_args.kwargs
    assert kwargs["project_name"] == "short_demo"
    assert kwargs["brief"]["short_form_format"] == "vertical_short"
    assert kwargs["render_profile"]["aspect_ratio"] == "9:16"
    assert kwargs["run_until"] == "storyboard"


def test_dispatch_short_form_job_rejects_invalid_run_depth():
    client = TestClient(create_app())

    resp = client.post(
        "/api/short-form/jobs",
        json={
            "project_name": "short_demo",
            "source_material": "Source notes",
            "run_until": "publish",
        },
    )

    assert resp.status_code == 400
    assert "storyboard, assets, or render" in resp.json()["detail"]["message"]
