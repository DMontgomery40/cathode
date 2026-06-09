"""Proves resolved credentials actually wire base_url into constructed clients.

Pure construction/string assertions — no network calls. A client built from a
proxy key must carry the configured base_url, never the public default.
"""

from __future__ import annotations

import pytest

from core import runtime, voice_gen

_PROVIDER_ENV_NAMES = (
    "OPENAI_API_KEY",
    "BETTUBE_STUDIO_OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "BETTUBE_STUDIO_OPENAI_BASE_URL",
    "BETTUBE_STUDIO_OPENAI_REALTIME_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "BETTUBE_STUDIO_ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "BETTUBE_STUDIO_ANTHROPIC_BASE_URL",
    "LITELLM_API_KEY",
    "AIPROXY_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch):
    for name in _PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


def test_make_openai_client_uses_configured_base_url(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "proxy-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8123/v1")
    client = runtime.make_openai_client()
    assert str(client.base_url).rstrip("/") == "http://127.0.0.1:8123/v1"


def test_make_openai_client_native_only_uses_public_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-native")
    client = runtime.make_openai_client()
    # No base_url configured -> SDK public default, proving we never force a proxy URL.
    assert "api.openai.com" in str(client.base_url)


def test_make_anthropic_client_uses_configured_base_url_and_auth_token(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "bearer-secret")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:8124")
    client = runtime.make_anthropic_client()
    assert str(client.base_url).rstrip("/") == "http://127.0.0.1:8124"
    # Bearer token routed via auth_token, not the x-api-key slot.
    assert client.auth_token == "bearer-secret"
    assert client.api_key in (None, "")


def test_realtime_url_derives_from_openai_base_url():
    url = voice_gen._resolve_openai_realtime_url("gpt-realtime-2", "https://proxy.internal/v1")
    assert url == "wss://proxy.internal/v1/realtime?model=gpt-realtime-2"


def test_realtime_url_defaults_to_public_when_no_base_url():
    url = voice_gen._resolve_openai_realtime_url("gpt-realtime-2", None)
    assert url == "wss://api.openai.com/v1/realtime?model=gpt-realtime-2"


def test_realtime_url_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("BETTUBE_STUDIO_OPENAI_REALTIME_URL", "wss://edge.internal/realtime")
    url = voice_gen._resolve_openai_realtime_url("gpt-realtime-2", "https://ignored/v1")
    assert url == "wss://edge.internal/realtime?model=gpt-realtime-2"
