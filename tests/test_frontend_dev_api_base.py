from pathlib import Path


def test_frontend_client_defaults_to_same_origin_api_base():
    client_source = Path("frontend/src/lib/api/client.ts").read_text()

    assert "const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'" in client_source
    assert "127.0.0.1:9321" not in client_source
