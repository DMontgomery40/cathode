import os
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
START_SCRIPT = REPO_ROOT / "start.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _prepare_launcher_fixture(tmp_path: Path) -> Path:
    fake_python = tmp_path / "fake_python.sh"
    _write_executable(
        fake_python,
        """#!/bin/sh
if [ "$1" = "-c" ]; then
  exit 0
fi
printf '%s\n' "$@" > "$FAKE_PYTHON_LOG"
""",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "npm",
        """#!/bin/sh
printf '%s\n' "$@" >> "$FAKE_NPM_LOG"
exit 0
""",
    )
    # wait_for_http polls with curl; always report ready.
    _write_executable(fake_bin / "curl", "#!/bin/sh\nexit 0\n")

    # Pre-create node_modules so the script skips npm install.
    (tmp_path / "frontend" / "node_modules").mkdir(parents=True)

    script_copy = tmp_path / "start.sh"
    script_text = START_SCRIPT.read_text().replace(
        'PYTHON="${BETTUBE_STUDIO_PYTHON:-$ROOT_DIR/.venv/bin/python}"',
        f'PYTHON="${{BETTUBE_STUDIO_PYTHON:-{fake_python}}}"',
        1,
    )
    _write_executable(script_copy, script_text)
    return script_copy


def _launcher_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path / 'bin'}{os.pathsep}{env['PATH']}"
    env["FAKE_PYTHON_LOG"] = str(tmp_path / "fake_python.log")
    env["FAKE_NPM_LOG"] = str(tmp_path / "fake_npm.log")
    return env


@pytest.mark.parametrize("cli_args", [[], ["--react"], ["--web"]])
def test_start_sh_defaults_to_react_stack(tmp_path: Path, cli_args: list[str]) -> None:
    script_copy = _prepare_launcher_fixture(tmp_path)
    env = _launcher_env(tmp_path)

    result = subprocess.run(
        ["/bin/bash", str(script_copy), *cli_args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "unbound variable" not in result.stderr

    uvicorn_args = (tmp_path / "fake_python.log").read_text().splitlines()
    assert uvicorn_args == [
        "-m",
        "uvicorn",
        "server.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "9321",
        "--reload",
    ]

    npm_calls = (tmp_path / "fake_npm.log").read_text()
    assert "run" in npm_calls and "dev" in npm_calls


def test_start_sh_help_no_longer_mentions_streamlit(tmp_path: Path) -> None:
    script_copy = _prepare_launcher_fixture(tmp_path)
    env = _launcher_env(tmp_path)

    result = subprocess.run(
        ["/bin/bash", str(script_copy), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "streamlit" not in result.stdout.lower()
    assert "FastAPI" in result.stdout
