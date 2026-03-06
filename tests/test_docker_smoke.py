from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


@pytest.mark.skipif(
    not os.getenv("RUN_DOCKER_TESTS"),
    reason="Set RUN_DOCKER_TESTS=1 to run Docker smoke coverage.",
)
def test_docker_image_starts_http_server(tmp_path):
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("docker is not installed")

    image_tag = "cathode-mcp:test"
    repo_root = Path(__file__).resolve().parent.parent

    subprocess.run([docker, "build", "-t", image_tag, "."], cwd=repo_root, check=True)

    container_name = "cathode-mcp-smoke"
    process = None
    try:
        process = subprocess.Popen(
            [
                docker,
                "run",
                "--rm",
                "--name",
                container_name,
                "-p",
                "8877:8765",
                image_tag,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        ps = subprocess.run(
            [docker, "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert container_name in ps.stdout
    finally:
        if process is not None:
            process.terminate()
        subprocess.run([docker, "rm", "-f", container_name], check=False)
