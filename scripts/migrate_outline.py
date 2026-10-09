#!/usr/bin/env python3
"""Migrate legacy Liquid Glass Slides outlines to the stable v2 protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from validate_outline import validate_outline
except ImportError:  # pragma: no cover - module execution fallback
    from scripts.validate_outline import validate_outline


def _slug(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    ascii_slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if ascii_slug:
        ascii_slug = ascii_slug[:56].rstrip("-")
        return ascii_slug if len(ascii_slug) >= 2 else ascii_slug + "-item"
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{fallback}-{digest}"


def _unique(candidate: str, used: set[str]) -> str:
    candidate = candidate[:64].rstrip("-")
    resolved = candidate
    suffix = 2
    while resolved in used:
        tail = f"-{suffix}"
        resolved = candidate[: 64 - len(tail)].rstrip("-") + tail
        suffix += 1
    used.add(resolved)
    return resolved


def migrate_outline(outline: Any, source_name: str = "deck") -> tuple[dict[str, Any], list[str]]:
    if not isinstance(outline, dict):
        raise ValueError("root must be a JSON object")
    source_version = outline.get("schema_version")
    if source_version not in (None, "1.0", "2.0"):
        raise ValueError(f"unsupported schema_version: {source_version}")

    title = outline.get("title") or "Liquid Glass Deck"
    deck_id = outline.get("deck_id") or _slug(source_name or title, "deck")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", str(deck_id)):
        deck_id = _slug(title, "deck")

    migrated: dict[str, Any] = {"schema_version": "2.0", "deck_id": deck_id}
    migrated.update({key: value for key, value in outline.items() if key not in {"schema_version", "deck_id", "slides"}})
    migrated.setdefault("title", title)
    migrated.setdefault("lang", "zh-CN")

    used: set[str] = set()
    changes: list[str] = []
    migrated_slides: list[Any] = []
    for index, raw_slide in enumerate(outline.get("slides", [])):
        if not isinstance(raw_slide, dict):
            migrated_slides.append(raw_slide)
            continue
        slide = dict(raw_slide)
        existing = slide.get("slide_id")
        if isinstance(existing, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", existing):
            slide_id = _unique(existing, used)
            if slide_id != existing:
                changes.append(f"slide {index + 1}: duplicate id {existing} renamed to {slide_id}")
        else:
            title_seed = slide.get("title") or slide.get("eyebrow") or slide.get("layout") or f"slide-{index + 1}"
            fallback = str(slide.get("layout") or "slide")
            slide_id = _unique(_slug(title_seed, fallback), used)
            changes.append(f"slide {index + 1}: assigned slide_id {slide_id}")
        migrated_slides.append({"slide_id": slide_id, **{k: v for k, v in slide.items() if k != "slide_id"}})
    migrated["slides"] = migrated_slides
    return migrated, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate a Liquid Glass Slides outline to schema v2.")
    parser.add_argument("outline", type=Path, help="Legacy or partially migrated outline")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--out", type=Path, help="Output path (default: <name>-v2.json)")
    output.add_argument("--in-place", action="store_true", help="Replace the input file")
    args = parser.parse_args()

    try:
        with args.outline.open("r", encoding="utf-8") as handle:
            outline = json.load(handle)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.outline}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            file=sys.stderr,
        )
        return 2

    try:
        migrated, changes = migrate_outline(outline, args.outline.stem)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_outline(migrated)
    if errors:
        print("MIGRATION FAILED VALIDATION:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    destination = args.outline if args.in_place else (
        args.out or args.outline.with_name(args.outline.stem + "-v2.json")
    )
    write_target = destination.with_suffix(destination.suffix + ".tmp") if args.in_place else destination
    try:
        with write_target.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(migrated, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if args.in_place:
            write_target.replace(destination)
    finally:
        if write_target != destination and write_target.exists():
            write_target.unlink()

    for change in changes:
        print(f"- {change}")
    print(f"MIGRATED: {args.outline} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
