"""Task-G regression: the one-click storyboard path works through an env-configured
OpenAI/Anthropic-compatible proxy, proven against a LOCAL mock on 127.0.0.1.

No public or corp endpoint is contacted. This locks the exact gap that previously
made make-video abort at the 'storyboard' stage under a proxy-only environment:
check_api_keys() reported anthropic unavailable and resolve_workflow_llm_roles()
raised before any storyboard was attempted.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core import director, runtime

_PROVIDER_ENV_NAMES = (
    "OPENAI_API_KEY",
    "BETTUBE_STUDIO_OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "BETTUBE_STUDIO_OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "BETTUBE_STUDIO_ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "BETTUBE_STUDIO_ANTHROPIC_BASE_URL",
    "LITELLM_API_KEY",
    "AIPROXY_API_KEY",
)

# Minimal valid Anthropic Messages tool-use response the SDK can parse into scenes.
_MOCK_MESSAGE = {
    "id": "msg_mock",
    "type": "message",
    "role": "assistant",
    "model": "claude-sonnet-4-6",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_mock",
            "name": "emit_storyboard",
            "input": {
                "scenes": [
                    {
                        "id": 0,
                        "title": "Mock Scene",
                        "narration": "Narration from the local mock proxy.",
                        "visual_prompt": "A calm still frame.",
                    }
                ]
            },
        }
    ],
    "stop_reason": "tool_use",
    "stop_sequence": None,
    "usage": {"input_tokens": 12, "output_tokens": 12},
}


class _MockAnthropicHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # pragma: no cover - silence test server logging
        pass

    def _respond(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        body = json.dumps(_MOCK_MESSAGE).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("request-id", "req_mock")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802 - http.server API
        self._respond()


@pytest.fixture()
def mock_anthropic_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockAnthropicHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch):
    for name in _PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


def test_proxy_only_env_opens_make_video_gate(monkeypatch, mock_anthropic_server):
    """A proxy key + ANTHROPIC_BASE_URL must light up the creative workflow gate."""
    monkeypatch.setenv("LITELLM_API_KEY", "dummy-proxy-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", mock_anthropic_server)

    assert runtime.check_api_keys()["anthropic"] is True
    # Previously raised ValueError at the storyboard stage; now resolves cleanly.
    assert runtime.resolve_workflow_llm_roles(None) == ("anthropic", "anthropic")


def test_storyboard_reaches_mock_proxy_and_returns_scenes(monkeypatch, mock_anthropic_server):
    monkeypatch.setenv("LITELLM_API_KEY", "dummy-proxy-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", mock_anthropic_server)

    # Force the director to rebuild its client against the mock env.
    monkeypatch.setattr(director, "_anthropic_client", None)

    client = director._get_anthropic_client()
    assert str(client.base_url).rstrip("/") == mock_anthropic_server

    scenes = director._generate_with_anthropic("system prompt", "user prompt")
    assert scenes
    assert scenes[0]["title"] == "Mock Scene"
