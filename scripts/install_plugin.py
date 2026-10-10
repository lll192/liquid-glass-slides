#!/usr/bin/env python3
"""Install Liquid Glass Slides as a local AI skill without external dependencies."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGED = (
    "SKILL.md", "LICENSE", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
    "agents", "assets", "console", "references", "scripts", "templates",
)
IGNORED_NAMES = {"__pycache__", ".test-tmp", ".git"}


def default_destination(target: str) -> Path:
    if target == "codex":
        return Path.home() / ".codex" / "skills" / "liquid-glass-slides"
    raise ValueError("--destination is required for custom installations")


def ignored(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES or name.endswith(".pyc")}


def install(destination: Path, *, update: bool, dry_run: bool) -> list[str]:
    destination = destination.expanduser().resolve()
    if destination == ROOT:
        raise ValueError("destination cannot be the source repository")
    if destination.exists() and not update:
        raise ValueError(f"destination already exists: {destination}; pass --update to refresh it")
    planned = [name for name in MANAGED if (ROOT / name).exists()]
    if dry_run:
        return planned
    destination.mkdir(parents=True, exist_ok=True)
    for name in planned:
        source = ROOT / name
        target = destination / name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignored)
        else:
            shutil.copy2(source, target)
    return planned


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Liquid Glass Slides as a local AI skill")
    parser.add_argument("--target", choices=("codex", "custom"), default="codex")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--update", action="store_true", help="refresh managed files in an existing install")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        destination = args.destination or default_destination(args.target)
        copied = install(destination, update=args.update, dry_run=args.dry_run)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    action = "Would install" if args.dry_run else "Installed"
    print(f"{action} Liquid Glass Slides at: {destination.expanduser().resolve()}")
    print("Managed components: " + ", ".join(copied))
    if not args.dry_run:
        print("Next: restart the AI client, then ask it to use $liquid-glass-slides.")
        print("Cockpit: python scripts/api_server.py --workspace <project-directory> --open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
