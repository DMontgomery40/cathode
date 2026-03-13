from pathlib import Path


def test_frontend_dev_client_uses_explicit_ipv4_backend_base():
    client_source = Path("frontend/src/lib/api/client.ts").read_text()

    assert "const DEV_API_BASE = 'http://127.0.0.1:9321/api'" in client_source
    assert "import.meta.env.DEV ? DEV_API_BASE : '/api'" in client_source
