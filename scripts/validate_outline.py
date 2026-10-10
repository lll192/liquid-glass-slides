#!/usr/bin/env python3
"""Validate the Liquid Glass Slides deck protocol v2 using only stdlib."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "2.0"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
LAYOUTS = {
    "cover", "toc", "section-divider", "bullets", "two-column",
    "grid-cards", "big-quote", "stat-highlight", "kpi-grid", "timeline",
    "comparison", "image-frame", "object-float", "closing", "chart",
    "data-table", "process-flow", "concept-map",
}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _optional_string(value: Any) -> bool:
    return value is None or isinstance(value, str)


def validate_outline(outline: Any) -> list[str]:
    """Return human-readable validation errors for a v2 outline."""
    errors: list[str] = []
    if not isinstance(outline, dict):
        return ["root must be a JSON object"]

    if outline.get("schema_version") != SCHEMA_VERSION:
        errors.append('schema_version must be "2.0"')

    deck_id = outline.get("deck_id")
    if not _nonempty_string(deck_id):
        errors.append("deck_id must be a non-empty string")
    elif not ID_RE.fullmatch(deck_id):
        errors.append("deck_id must use 2-64 lowercase letters, numbers, or hyphens")

    for field in ("title", "lang"):
        if not _nonempty_string(outline.get(field)):
            errors.append(f"{field} must be a non-empty string")

    for field in ("brief", "theme", "output"):
        value = outline.get(field)
        if value is not None and not isinstance(value, dict):
            errors.append(f"{field} must be an object when provided")
    sources = outline.get("sources")
    if sources is not None and (
        not isinstance(sources, list) or not all(isinstance(item, dict) for item in sources)
    ):
        errors.append("sources must be an array of objects when provided")

    if outline.get("composition") not in (None, "constructivist", "classic"):
        errors.append("composition must be constructivist or classic when provided")
    if outline.get("typography") not in (None, "editorial", "classic"):
        errors.append("typography must be editorial or classic when provided")

    for field in (
        "layout_intelligence", "visual_intelligence", "quality_intelligence",
        "content_intelligence", "narrative_director", "visual_coverage_planner",
        "auto_ripple",
    ):
        value = outline.get(field)
        if value is not None and not isinstance(value, bool):
            errors.append(f"{field} must be a boolean when provided")

    slides = outline.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("slides must be a non-empty array")
        slides = []
    elif len(slides) > 100:
        errors.append("slides must contain at most 100 pages")

    seen_ids: set[str] = set()
    for index, slide in enumerate(slides):
        prefix = f"slides[{index}]"
        if not isinstance(slide, dict):
            errors.append(f"{prefix} must be an object")
            continue
        slide_id = slide.get("slide_id")
        if not _nonempty_string(slide_id):
            errors.append(f"{prefix}.slide_id must be a non-empty string")
        elif not ID_RE.fullmatch(slide_id):
            errors.append(
                f"{prefix}.slide_id must use 2-64 lowercase letters, numbers, or hyphens"
            )
        elif slide_id in seen_ids:
            errors.append(f"{prefix}.slide_id duplicates {slide_id}")
        else:
            seen_ids.add(slide_id)

        layout = slide.get("layout")
        if layout not in LAYOUTS:
            errors.append(f"{prefix}.layout must be one of: " + ", ".join(sorted(LAYOUTS)))

        notes = slide.get("speaker_notes", slide.get("notes"))
        if notes is not None:
            valid_notes = _nonempty_string(notes) or (
                isinstance(notes, list)
                and bool(notes)
                and all(_nonempty_string(item) for item in notes)
            )
            if not valid_notes:
                errors.append(
                    f"{prefix}.speaker_notes must be a non-empty string or array of non-empty strings"
                )

        for field in (
            "main_point", "audience_question", "speaker_intent", "transition", "emotion",
        ):
            if not _optional_string(slide.get(field)):
                errors.append(f"{prefix}.{field} must be a string when provided")

        visual_plan = slide.get("visual_plan")
        if visual_plan is not None and not isinstance(visual_plan, dict):
            errors.append(f"{prefix}.visual_plan must be an object when provided")

        hero_mode = slide.get("hero_mode")
        if hero_mode is not None and hero_mode not in {"auto", "float", "frame"}:
            errors.append(f"{prefix}.hero_mode must be auto, float, or frame")
        hero_fit = slide.get("hero_fit")
        if hero_fit is not None and hero_fit not in {"contain", "cover"}:
            errors.append(f"{prefix}.hero_fit must be contain or cover")
        hero_position = slide.get("hero_position")
        if hero_position is not None and (
            not isinstance(hero_position, str)
            or not re.fullmatch(r"\d{1,3}%\s+\d{1,3}%", hero_position.strip())
        ):
            errors.append(f"{prefix}.hero_position must look like 50% 50%")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Liquid Glass Slides v2 outline.")
    parser.add_argument("outline", type=Path, help="Path to outline.json")
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

    errors = validate_outline(outline)
    if errors:
        print(f"INVALID: {args.outline}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"VALID: {args.outline} ({len(outline['slides'])} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
