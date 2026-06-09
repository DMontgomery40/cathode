#!/usr/bin/env python3
"""Repository-wide legacy brand migration helper.

The script is intentionally context-aware:

- shell/environment variables use BETTUBE_STUDIO_*
- Python/TypeScript identifiers use bettube_studio
- user-facing slugs, paths, package names, and hidden directories use bettube-studio
- visible title-case product mentions use betTube Studio

Run without --apply for a dry run. Add --everything when you also want ignored
local project state, local config files, and project-local Codex memory migrated.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


LEGACY = "cat" "hode"
LEGACY_TITLE = LEGACY.capitalize()
LEGACY_ENV = LEGACY.upper()

NEW_TITLE = "betTube Studio"
NEW_SLUG = "bettube-studio"
NEW_IDENT = "bettube_studio"
NEW_ENV = "BETTUBE_STUDIO"

ALWAYS_EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "ENV",
    "node_modules",
    "dist",
    "build",
    "eggs",
    ".eggs",
    "sdist",
    "wheels",
    "downloads",
}

DEFAULT_EXCLUDED_DIR_NAMES = {
    ".logos",
    ".playwright-mcp",
    ".v1-videos",
    "experiments",
    "frontend/projects",
    "frontend/test-results",
    "output",
    "projects",
    "reference_frames",
}

LOCAL_CONFIG_NAMES = {
    ".env",
    ".envrc",
    ".netrc",
    ".npmrc",
    "frontend/.npmrc",
    "pip.conf",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".csv",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".lock",
    ".md",
    ".mjs",
    ".py",
    ".pyi",
    ".sh",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
    ".zsh",
}

CODE_SUFFIXES = {
    ".cjs",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".pyi",
    ".sh",
    ".ts",
    ".tsx",
    ".zsh",
}


@dataclass(frozen=True)
class TextChange:
    path: Path
    old_text: str
    new_text: str


@dataclass(frozen=True)
class PathMove:
    source: Path
    target: Path


def build_common_replacements() -> list[tuple[str, str]]:
    skill_suffixes = [
        "project-demo",
        "remotion-development",
        "short-form-vertical-video",
    ]
    replacements: list[tuple[str, str]] = [
        (LEGACY_ENV + "_", NEW_ENV + "_"),
        (LEGACY_ENV, NEW_ENV),
        (f"{LEGACY}_mcp_server", f"{NEW_IDENT}_mcp_server"),
        (f"test_{LEGACY}_mcp_server", f"test_{NEW_IDENT}_mcp_server"),
        (f"test_{LEGACY}_project_demo", f"test_{NEW_IDENT}_project_demo"),
        (f"bootstrap_{LEGACY}", f"bootstrap_{NEW_IDENT}"),
        (f"prepare_{LEGACY}_handoff", f"prepare_{NEW_IDENT}_handoff"),
        (f"{LEGACY}_make_video_payload", f"{NEW_IDENT}_make_video_payload"),
        (f"{LEGACY}-remotion-architecture", f"{NEW_SLUG}-remotion-architecture"),
        (f"{LEGACY}-workflow-behind-scenes", f"{NEW_SLUG}-workflow-behind-scenes"),
        (f"{LEGACY}-demo-youtube-card", f"{NEW_SLUG}-demo-youtube-card"),
        (f"{LEGACY}-logo", f"{NEW_SLUG}-logo"),
        (f".{LEGACY}", f".{NEW_SLUG}"),
        (f"{LEGACY}-ui", f"{NEW_SLUG}-ui"),
        (f"{LEGACY}:last-project-id", f"{NEW_SLUG}:last-project-id"),
        (f"{LEGACY}-codex-image", f"{NEW_SLUG}-codex-image"),
        (f"{LEGACY}-scene-review", f"{NEW_SLUG}-scene-review"),
        (f"{LEGACY}.git", f"{NEW_SLUG}.git"),
        (f"{LEGACY}/", f"{NEW_SLUG}/"),
        (f"/{LEGACY}", f"/{NEW_SLUG}"),
        (f'"{LEGACY}"', f'"{NEW_SLUG}"'),
        (f"'{LEGACY}'", f"'{NEW_SLUG}'"),
        (f"`{LEGACY}`", f"`{NEW_SLUG}`"),
        (f"{LEGACY_TITLE}'s", f"{NEW_TITLE}'s"),
        (LEGACY_TITLE, NEW_TITLE),
    ]
    for suffix in skill_suffixes:
        replacements.append((f"{LEGACY}-{suffix}", f"{NEW_SLUG}-{suffix}"))
    return replacements


COMMON_REPLACEMENTS = build_common_replacements()


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename the legacy internal brand across source, paths, and optional local state.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root_from_script(),
        help="Repository root to migrate. Defaults to this script's repository.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write content changes and perform path moves. Omit for dry run.",
    )
    parser.add_argument(
        "--include-generated",
        action="store_true",
        help="Also scan ignored generated/local project state such as projects/ and output/.",
    )
    parser.add_argument(
        "--include-local-config",
        action="store_true",
        help="Also scan local config files such as .env and .npmrc.",
    )
    parser.add_argument(
        "--include-codex-memory",
        action="store_true",
        help="Also migrate project-local Codex memory under ~/.codex/projects when present.",
    )
    parser.add_argument(
        "--everything",
        action="store_true",
        help="Shortcut for --include-generated --include-local-config --include-codex-memory.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the summary and problems.",
    )
    return parser.parse_args()


def rel_key(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_under_named_dir(root: Path, path: Path, names: set[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    parts = rel.parts
    if not parts:
        return False
    joined_prefixes = {"/".join(parts[: index + 1]) for index in range(len(parts))}
    return any(part in names for part in parts) or bool(joined_prefixes & names)


def should_exclude(root: Path, path: Path, args: argparse.Namespace) -> bool:
    if path == root:
        return False
    if is_under_named_dir(root, path, ALWAYS_EXCLUDED_DIR_NAMES):
        return True
    if not args.include_generated and is_under_named_dir(root, path, DEFAULT_EXCLUDED_DIR_NAMES):
        return True
    if not args.include_local_config:
        rel = rel_key(root, path)
        name = path.name
        if rel in LOCAL_CONFIG_NAMES or name in LOCAL_CONFIG_NAMES:
            return True
        if name.startswith(".env.") and name != ".env.example":
            return True
    return False


def iter_paths(root: Path, args: argparse.Namespace, include_root: bool = False) -> list[Path]:
    paths: list[Path] = [root] if include_root else []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = [
            dirname
            for dirname in dirs
            if not should_exclude(root, current_path / dirname, args)
        ]
        for filename in files:
            path = current_path / filename
            if not should_exclude(root, path, args):
                paths.append(path)
        for dirname in dirs:
            paths.append(current_path / dirname)
    return paths


def looks_like_text(path: Path) -> bool:
    if path.suffix in TEXT_SUFFIXES:
        return True
    if path.name in {"Dockerfile", "README.md", ".gitignore", ".dockerignore"}:
        return True
    return False


def read_text(path: Path) -> str | None:
    if not looks_like_text(path):
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:8192]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def apply_common_replacements(text: str) -> str:
    for old, new in COMMON_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def replace_code_contexts(text: str) -> str:
    text = text.replace(f"{LEGACY}_", f"{NEW_IDENT}_")
    text = text.replace(f"_{LEGACY}", f"_{NEW_IDENT}")
    text = text.replace(f"{LEGACY}.", f"{NEW_IDENT}.")
    text = re.sub(rf"\bas\s+{re.escape(LEGACY)}\b", f"as {NEW_IDENT}", text)
    text = re.sub(rf"\b{re.escape(LEGACY)}\b", NEW_IDENT, text)
    return text


def replace_prose_contexts(text: str) -> str:
    text = text.replace(f"{LEGACY}_", f"{NEW_IDENT}_")
    text = text.replace(f"_{LEGACY}", f"_{NEW_IDENT}")
    text = re.sub(rf"\b{re.escape(LEGACY)}\b", NEW_SLUG, text)
    return text


def transform_text(path: Path, text: str) -> str:
    transformed = apply_common_replacements(text)
    if path.suffix in CODE_SUFFIXES:
        return replace_code_contexts(transformed)
    return replace_prose_contexts(transformed)


def transform_path_part(part: str) -> str:
    transformed = apply_common_replacements(part)
    if LEGACY not in transformed and LEGACY_TITLE not in transformed and LEGACY_ENV not in transformed:
        return transformed
    codeish = part.endswith(".py") or "_" in part
    if codeish:
        transformed = transformed.replace(f"{LEGACY}_", f"{NEW_IDENT}_")
        transformed = transformed.replace(f"_{LEGACY}", f"_{NEW_IDENT}")
        transformed = transformed.replace(LEGACY, NEW_IDENT)
    else:
        transformed = transformed.replace(LEGACY, NEW_SLUG)
    transformed = transformed.replace(LEGACY_TITLE, NEW_SLUG)
    transformed = transformed.replace(LEGACY_ENV, NEW_ENV)
    return transformed


def transformed_path(path: Path) -> Path:
    target = path.with_name(transform_path_part(path.name))
    return target


def collect_text_changes(roots: list[tuple[Path, bool]], args: argparse.Namespace) -> list[TextChange]:
    changes: list[TextChange] = []
    for root, include_root in roots:
        for path in iter_paths(root, args, include_root=include_root):
            if path.is_dir():
                continue
            old_text = read_text(path)
            if old_text is None:
                continue
            new_text = transform_text(path, old_text)
            if new_text != old_text:
                changes.append(TextChange(path=path, old_text=old_text, new_text=new_text))
    return changes


def collect_path_moves(roots: list[tuple[Path, bool]], args: argparse.Namespace) -> list[PathMove]:
    moves: list[PathMove] = []
    for root, include_root in roots:
        for path in iter_paths(root, args, include_root=include_root):
            target = transformed_path(path)
            if target != path:
                moves.append(PathMove(source=path, target=target))
    moves.sort(key=lambda move: (len(move.source.parts), move.source.is_file()), reverse=True)
    return moves


def legacy_needles() -> tuple[str, str, str]:
    return (LEGACY, LEGACY_TITLE, LEGACY_ENV)


def contains_legacy(text: str) -> bool:
    return any(needle in text for needle in legacy_needles())


def residual_text_hits(roots: list[tuple[Path, bool]], args: argparse.Namespace) -> list[str]:
    hits: list[str] = []
    for root, include_root in roots:
        for path in iter_paths(root, args, include_root=include_root):
            if path.is_dir():
                continue
            old_text = read_text(path)
            if old_text is None:
                continue
            transformed = transform_text(path, old_text)
            if contains_legacy(transformed):
                hits.append(str(path))
    return sorted(set(hits))


def residual_path_hits(moves: list[PathMove], roots: list[tuple[Path, bool]], args: argparse.Namespace) -> list[str]:
    hit_paths: list[str] = []
    move_by_source = {move.source: move.target for move in moves}
    for root, include_root in roots:
        for path in iter_paths(root, args, include_root=include_root):
            target = move_by_source.get(path, path)
            if contains_legacy(target.name):
                hit_paths.append(str(path))
    return sorted(set(hit_paths))


def ensure_no_collisions(moves: list[PathMove]) -> None:
    targets = [move.target for move in moves]
    duplicate_targets = sorted({target for target in targets if targets.count(target) > 1})
    if duplicate_targets:
        joined = "\n".join(f"  {target}" for target in duplicate_targets)
        raise RuntimeError(f"Multiple sources would move to the same target:\n{joined}")
    collisions = [
        move
        for move in moves
        if move.target.exists() and move.target.resolve() != move.source.resolve()
    ]
    if collisions:
        joined = "\n".join(f"  {move.source} -> {move.target}" for move in collisions)
        raise RuntimeError(f"Refusing to overwrite existing paths:\n{joined}")


def write_text_changes(changes: list[TextChange]) -> None:
    for change in changes:
        newline = "\n" if change.old_text.endswith("\n") else ""
        text = change.new_text
        if newline and not text.endswith("\n"):
            text += "\n"
        change.path.write_text(text, encoding="utf-8")


def perform_path_moves(moves: list[PathMove]) -> None:
    for move in moves:
        if not move.source.exists():
            continue
        move.target.parent.mkdir(parents=True, exist_ok=True)
        move.source.rename(move.target)


def git_status(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return ""
    return completed.stdout.strip()


def codex_memory_roots(args: argparse.Namespace) -> list[Path]:
    if not args.include_codex_memory:
        return []
    old_root = Path.home() / ".codex" / "projects" / f"-Users-davidmontgomery-{LEGACY}"
    return [old_root] if old_root.exists() else []


def print_summary(
    *,
    args: argparse.Namespace,
    roots: list[tuple[Path, bool]],
    changes: list[TextChange],
    moves: list[PathMove],
    residual_text: list[str],
    residual_paths: list[str],
) -> None:
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"{mode}: {len(changes)} text file(s), {len(moves)} path move(s)")
    for root, include_root in roots:
        marker = " including root path" if include_root else ""
        print(f"  root: {root}{marker}")
    if not args.quiet:
        if changes:
            print("\nText changes:")
            for change in changes:
                print(f"  {change.path}")
        if moves:
            print("\nPath moves:")
            for move in moves:
                print(f"  {move.source} -> {move.target}")
    if residual_text:
        print("\nResidual text needing manual handling after transformation:")
        for path in residual_text:
            print(f"  {path}")
    if residual_paths:
        print("\nResidual path names needing manual handling after transformation:")
        for path in residual_paths:
            print(f"  {path}")


def main() -> int:
    args = parse_args()
    if args.everything:
        args.include_generated = True
        args.include_local_config = True
        args.include_codex_memory = True

    repo_root = args.repo_root.expanduser().resolve()
    if not repo_root.exists():
        print(f"Repository root does not exist: {repo_root}", file=sys.stderr)
        return 2

    roots: list[tuple[Path, bool]] = [(repo_root, False)]
    roots.extend((root, True) for root in codex_memory_roots(args))

    changes = collect_text_changes(roots, args)
    moves = collect_path_moves(roots, args)
    residual_text = residual_text_hits(roots, args)
    residual_paths = residual_path_hits(moves, roots, args)

    try:
        ensure_no_collisions(moves)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print_summary(
        args=args,
        roots=roots,
        changes=changes,
        moves=moves,
        residual_text=residual_text,
        residual_paths=residual_paths,
    )

    if residual_text or residual_paths:
        print("\nResolve the residual items before applying.", file=sys.stderr)
        return 4

    if args.apply:
        if status := git_status(repo_root):
            print("\nExisting git status before applying:")
            print(status)
        write_text_changes(changes)
        perform_path_moves(moves)
        print("\nApplied migration.")
    else:
        print("\nDry run only. Re-run with --apply to write changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
