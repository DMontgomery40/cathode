"""Env-driven provider credential resolution (corp LiteLLM/AIProxy drop-in).

These tests pin the leak-safe contract: a provider-native key works against the
public endpoint (back-compat), while a shared/proxy key only counts toward a
provider AND is only ever paired with that provider's *_BASE_URL, so a corp key
is never sent to a public endpoint and never leaks across providers.
"""

from __future__ import annotations

import pytest

from core import runtime

# Every provider env name the resolver consults — cleared before each test so the
# ambient shell (which may already export ANTHROPIC_*/LITELLM_*/AIPROXY_*) cannot
# leak into the assertions.
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
    "REPLICATE_API_TOKEN",
    "DASHSCOPE_API_KEY",
    "ALIBABA_API_KEY",
    "ELEVENLABS_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_provider_env(monkeypatch):
    for name in _PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    yield


def test_native_openai_key_only_is_available_without_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-native")
    creds = runtime.resolve_openai_credentials()
    assert creds["available"] is True
    assert creds["is_native"] is True
    assert creds["base_url"] is None
    # Back-compat: no base_url -> no kwargs injected, SDK reads OPENAI_API_KEY itself.
    assert runtime.openai_client_kwargs() == {}


def test_native_anthropic_key_only_is_available_without_base_url(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-native")
    creds = runtime.resolve_anthropic_credentials()
    assert creds["available"] is True
    assert creds["is_native"] is True
    assert creds["base_url"] is None
    assert runtime.anthropic_client_kwargs() == {}


@pytest.mark.parametrize("proxy_name", ["LITELLM_API_KEY", "AIPROXY_API_KEY"])
def test_proxy_key_without_base_url_is_not_available(monkeypatch, proxy_name):
    """The leak guard: a proxy key with no base_url enables nothing and is never sent."""
    monkeypatch.setenv(proxy_name, "proxy-secret")
    assert runtime.resolve_openai_credentials()["available"] is False
    assert runtime.resolve_anthropic_credentials()["available"] is False
    assert runtime.openai_client_kwargs() == {}
    assert runtime.anthropic_client_kwargs() == {}
    assert runtime.check_api_keys()["openai"] is False
    assert runtime.check_api_keys()["anthropic"] is False


def test_proxy_key_with_base_url_is_available_and_pairs_kwargs(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "proxy-secret")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.internal/anthropic")
    creds = runtime.resolve_anthropic_credentials()
    assert creds["available"] is True
    assert creds["api_key"] == "proxy-secret"
    assert creds["base_url"] == "https://proxy.internal/anthropic"
    # api_key + base_url delivered as a matched pair (x-api-key slot here).
    assert runtime.anthropic_client_kwargs() == {
        "api_key": "proxy-secret",
        "base_url": "https://proxy.internal/anthropic",
    }


def test_key_precedence_native_beats_proxy(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "native")
    monkeypatch.setenv("BETTUBE_STUDIO_OPENAI_API_KEY", "app-namespaced")
    monkeypatch.setenv("LITELLM_API_KEY", "proxy")
    creds = runtime.resolve_openai_credentials()
    assert creds["api_key"] == "native"
    assert creds["api_key_source"] == "OPENAI_API_KEY"


def test_anthropic_auth_token_routes_as_auth_token(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "bearer-secret")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.internal/anthropic")
    creds = runtime.resolve_anthropic_credentials()
    assert creds["use_auth_token"] is True
    # Bearer token must go in the auth_token slot, never api_key (x-api-key).
    kwargs = runtime.anthropic_client_kwargs()
    assert kwargs == {
        "auth_token": "bearer-secret",
        "base_url": "https://proxy.internal/anthropic",
    }


def test_shared_key_does_not_leak_across_providers(monkeypatch):
    """A shared proxy key with only OPENAI_BASE_URL enables OpenAI, never Anthropic."""
    monkeypatch.setenv("LITELLM_API_KEY", "proxy-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.internal/openai/v1")
    assert runtime.resolve_openai_credentials()["available"] is True
    assert runtime.resolve_anthropic_credentials()["available"] is False
    # The proxy key is paired only with the OpenAI endpoint; Anthropic gets nothing.
    assert runtime.openai_client_kwargs() == {
        "api_key": "proxy-secret",
        "base_url": "https://proxy.internal/openai/v1",
    }
    assert runtime.anthropic_client_kwargs() == {}


def test_check_api_keys_reflects_resolution(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.internal/anthropic")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "rep")
    keys = runtime.check_api_keys()
    assert keys["anthropic"] is True
    assert keys["openai"] is False
    assert keys["replicate"] is True
    assert keys["dashscope"] is False
    assert keys["elevenlabs"] is False


def test_empty_env_reports_no_llm_providers():
    assert runtime.check_api_keys()["openai"] is False
    assert runtime.check_api_keys()["anthropic"] is False
    with pytest.raises(ValueError):
        runtime.choose_llm_provider()
    with pytest.raises(ValueError):
        runtime.resolve_workflow_llm_roles(None)
