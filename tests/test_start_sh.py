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

    script_copy = tmp_path / "start.sh"
    script_text = START_SCRIPT.read_text().replace(
        'PYTHON="/opt/homebrew/bin/python3.10"',
        f'PYTHON="{fake_python}"',
        1,
    )
    _write_executable(script_copy, script_text)
    return script_copy


@pytest.mark.parametrize(
    ("cli_args", "expected_tail"),
    [
        ([], []),
        (["--"], []),
        (
            ["--streamlit", "--", "--browser.gatherUsageStats=false", "--logger.level=debug"],
            ["--browser.gatherUsageStats=false", "--logger.level=debug"],
        ),
    ],
)
def test_start_sh_streamlit_handles_optional_extra_args(tmp_path: Path, cli_args: list[str], expected_tail: list[str]) -> None:
    script_copy = _prepare_launcher_fixture(tmp_path)
    log_path = tmp_path / "fake_python.log"

    env = os.environ.copy()
    env["FAKE_PYTHON_LOG"] = str(log_path)

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
    assert log_path.read_text().splitlines() == [
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        "8517",
        *expected_tail,
    ]
