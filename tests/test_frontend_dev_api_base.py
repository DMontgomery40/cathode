from pathlib import Path


def test_frontend_client_api_base_is_env_driven():
    """API_BASE must come from VITE_API_BASE_URL (deploy-time config), defaulting to
    same-origin relative paths so the Vite dev proxy and the FastAPI-served SPA both work."""
    client_source = Path("frontend/src/lib/api/client.ts").read_text()

    assert "import.meta.env.VITE_API_BASE_URL" in client_source
    assert "?? ''" in client_source
    # No hardcoded backend host may sneak back in.
    assert "http://127.0.0.1" not in client_source
    assert "http://localhost" not in client_source
