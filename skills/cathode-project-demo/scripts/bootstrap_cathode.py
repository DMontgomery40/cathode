#!/usr/bin/env python3
"""Prepare a Cathode checkout for skill-driven app or MCP usage."""

from __future__ import annotations

import argparse
import json
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO_URL = "https://github.com/DMontgomery40/cathode.git"
DEFAULT_CHECKOUT_DIR = Path.home() / ".cache" / "cathode"


class BootstrapError(RuntimeError):
    """Raised when the checkout cannot be prepared safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or reuse a Cathode checkout and emit launch commands as JSON.",
    )
    parser.add_argument(
        "--repo-path",
        help="Existing Cathode checkout to reuse. The script will not pull or checkout refs in this mode.",
    )
    parser.add_argument(
        "--checkout-dir",
        default=str(DEFAULT_CHECKOUT_DIR),
        help=f"Managed checkout directory used when --repo-path is omitted. Default: {DEFAULT_CHECKOUT_DIR}",
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help=f"Git URL used when cloning a managed checkout. Default: {DEFAULT_REPO_URL}",
    )
    parser.add_argument(
        "--ref",
        help="Optional branch or tag to checkout for managed clones.",
    )
    parser.add_argument(
        "--python",
        dest="python_bin",
        help="Explicit Python 3.10 executable to use for the Cathode virtualenv.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Fetch and fast-forward the managed checkout when it already exists.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip pip install even when the virtualenv is new.",
    )
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="Force pip install -r requirements.txt even when the virtualenv already exists.",
    )
    parser.add_argument(
        "--streamlit-port",
        type=int,
        default=8517,
        help="Port included in the emitted Streamlit launch command. Default: 8517",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=8765,
        help="Port included in the emitted HTTP MCP launch command. Default: 8765",
    )
    return parser.parse_args()


def _run(cmd: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture,
    )


def _candidate_paths(explicit: str | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if sys.version_info[:2] == (3, 10):
        candidates.append(Path(sys.executable))
    for raw in ("python3.10", "/opt/homebrew/bin/python3.10", "/usr/local/bin/python3.10"):
        resolved = shutil.which(raw) if "/" not in raw else raw
        if resolved:
            candidates.append(Path(resolved))
    return candidates


def _probe_python(candidate: Path) -> bool:
    try:
        completed = _run(
            [str(candidate), "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            capture=True,
        )
    except Exception:
        return False
    return completed.stdout.strip() == "3.10"


def find_python(explicit: str | None) -> Path:
    seen: set[str] = set()
    for candidate in _candidate_paths(explicit):
        resolved = str(candidate)
        if resolved in seen:
            continue
        seen.add(resolved)
        if _probe_python(candidate):
            return Path(resolved).resolve()
    raise BootstrapError("Python 3.10 is required for Cathode. Install python3.10 or pass --python /path/to/python3.10.")


def validate_repo(repo_path: Path) -> None:
    required = ("app.py", "cathode_mcp_server.py", "requirements.txt")
    missing = [name for name in required if not (repo_path / name).exists()]
    if missing:
        joined = ", ".join(missing)
        raise BootstrapError(f"{repo_path} does not look like a Cathode checkout. Missing: {joined}")


def clone_or_reuse_checkout(args: argparse.Namespace) -> tuple[Path, bool]:
    if args.repo_path:
        repo_path = Path(args.repo_path).expanduser().resolve()
        if not repo_path.exists():
            raise BootstrapError(f"Explicit --repo-path does not exist: {repo_path}")
        validate_repo(repo_path)
        return repo_path, False

    repo_path = Path(args.checkout_dir).expanduser().resolve()
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if not repo_path.exists() or (repo_path.is_dir() and not any(repo_path.iterdir())):
        _run(["git", "clone", args.repo_url, str(repo_path)])
        if args.ref:
            _run(["git", "checkout", args.ref], cwd=repo_path)
    elif args.update:
        _run(["git", "fetch", "--all", "--tags", "--prune"], cwd=repo_path)
        if args.ref:
            _run(["git", "checkout", args.ref], cwd=repo_path)
        else:
            branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path, capture=True).stdout.strip()
            if branch == "HEAD":
                raise BootstrapError("Managed checkout is in a detached HEAD state. Pass --ref or recreate the checkout.")
            _run(["git", "pull", "--ff-only", "origin", branch], cwd=repo_path)
    else:
        validate_repo(repo_path)

    validate_repo(repo_path)
    return repo_path, True


def ensure_venv(repo_path: Path, python_bin: Path, *, skip_install: bool, reinstall: bool) -> tuple[Path, bool, bool]:
    venv_dir = repo_path / ".venv"
    venv_python = venv_dir / "bin" / "python"
    venv_created = False

    if not venv_python.exists():
        _run([str(python_bin), "-m", "venv", str(venv_dir)])
        venv_created = True

    should_install = not skip_install and (venv_created or reinstall)
    if should_install:
        _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], cwd=repo_path)
        _run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], cwd=repo_path)

    return venv_python, venv_created, should_install


def detect_system_dependencies() -> tuple[dict[str, str | None], list[str]]:
    found = {
        "ffmpeg": shutil.which("ffmpeg"),
        "espeak-ng": shutil.which("espeak-ng"),
    }
    missing = [name for name, location in found.items() if not location]
    return found, missing


def install_hint() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "brew install python@3.10 ffmpeg espeak-ng"
    if system == "linux":
        return "sudo apt-get install python3.10 ffmpeg espeak-ng"
    return "Install Python 3.10, ffmpeg, and espeak-ng with your system package manager."


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def build_output(
    *,
    repo_path: Path,
    managed_checkout: bool,
    python_bin: Path,
    venv_python: Path,
    venv_created: bool,
    dependencies_installed: bool,
    streamlit_port: int,
    mcp_port: int,
) -> dict[str, object]:
    env_example = repo_path / ".env.example"
    found, missing = detect_system_dependencies()

    app_command = [
        str(venv_python),
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        str(streamlit_port),
    ]
    mcp_stdio_command = [str(venv_python), "cathode_mcp_server.py", "--transport", "stdio"]
    mcp_http_command = [
        "env",
        f"CATHODE_MCP_PORT={mcp_port}",
        str(venv_python),
        "cathode_mcp_server.py",
        "--transport",
        "streamable-http",
    ]

    notes = [
        "Set OPENAI_API_KEY or ANTHROPIC_API_KEY before calling make_video.",
        "Cathode now prefers the local Codex Exec + GPT Image lane for stills when codex and OPENAI_API_KEY are available. REPLICATE_API_TOKEN remains a fallback image path.",
    ]
    if missing:
        notes.append(f"Missing system dependencies: {', '.join(missing)}. Suggested install: {install_hint()}")
    if env_example.exists():
        notes.append(f"Optional environment template: {env_example}")

    return {
        "repo_path": str(repo_path),
        "managed_checkout": managed_checkout,
        "python_executable": str(python_bin),
        "venv_python": str(venv_python),
        "venv_created": venv_created,
        "dependencies_installed": dependencies_installed,
        "projects_dir": str(repo_path / "projects"),
        "env_example_path": str(env_example) if env_example.exists() else None,
        "system_dependencies": found,
        "missing_system_dependencies": missing,
        "install_hint": install_hint(),
        "app_command": shell_join(app_command),
        "mcp_stdio_command": shell_join(mcp_stdio_command),
        "mcp_http_command": shell_join(mcp_http_command),
        "notes": notes,
    }


def main() -> int:
    args = parse_args()
    try:
        repo_path, managed_checkout = clone_or_reuse_checkout(args)
        python_bin = find_python(args.python_bin)
        venv_python, venv_created, dependencies_installed = ensure_venv(
            repo_path,
            python_bin,
            skip_install=args.skip_install,
            reinstall=args.reinstall,
        )
        payload = build_output(
            repo_path=repo_path,
            managed_checkout=managed_checkout,
            python_bin=python_bin,
            venv_python=venv_python,
            venv_created=venv_created,
            dependencies_installed=dependencies_installed,
            streamlit_port=args.streamlit_port,
            mcp_port=args.mcp_port,
        )
    except BootstrapError as exc:
        payload = {"status": "error", "error": str(exc), "install_hint": install_hint()}
        print(json.dumps(payload, indent=2))
        return 1
    except subprocess.CalledProcessError as exc:
        payload = {
            "status": "error",
            "error": f"Command failed with exit code {exc.returncode}: {' '.join(exc.cmd)}",
            "stderr": exc.stderr or "",
            "stdout": exc.stdout or "",
        }
        print(json.dumps(payload, indent=2))
        return 1
    except FileNotFoundError as exc:
        payload = {
            "status": "error",
            "error": f"Required command not found: {exc.filename}",
            "install_hint": install_hint(),
        }
        print(json.dumps(payload, indent=2))
        return 1

    payload["status"] = "ok"
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
