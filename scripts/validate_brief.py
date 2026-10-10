#!/usr/bin/env python3
"""Validate a liquid-glass-slides design brief using only the stdlib."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCENARIOS = {"teaching", "report", "pitch", "interview", "keynote", "internal", "general"}
CONTENT_MODES = {"supplied", "assisted", "agent-led"}
DIRECTIONS = {"auto", "minimal", "academic", "technology", "warm", "brand"}
DENSITIES = {"airy", "balanced", "dense"}
MOTIONS = {"none", "subtle", "expressive"}
MEDIA_LEVELS = {"restrained", "balanced", "rich"}
PRODUCTION_PROFILES = {"fast", "balanced", "premium"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def validate_brief(brief: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(brief, dict):
        return ["root must be a JSON object"]

    if brief.get("schema_version") != "1.0":
        errors.append('schema_version must be "1.0"')

    for field in ("topic", "objective", "audience", "language"):
        if not _nonempty_string(brief.get(field)):
            errors.append(f"{field} must be a non-empty string")

    if brief.get("scenario") not in SCENARIOS:
        errors.append("scenario must be one of: " + ", ".join(sorted(SCENARIOS)))

    slide_count = brief.get("slide_count")
    if isinstance(slide_count, bool) or not isinstance(slide_count, int) or not 3 <= slide_count <= 40:
        errors.append("slide_count must be an integer from 3 to 40")

    duration = brief.get("duration_minutes")
    if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0):
        errors.append("duration_minutes must be a positive number or null")

    content = brief.get("content")
    if not isinstance(content, dict):
        errors.append("content must be an object")
    else:
        if content.get("mode") not in CONTENT_MODES:
            errors.append("content.mode must be one of: " + ", ".join(sorted(CONTENT_MODES)))
        for field in ("source_files", "must_include", "avoid"):
            if not _string_list(content.get(field)):
                errors.append(f"content.{field} must be an array of non-empty strings")

    visual = brief.get("visual")
    if not isinstance(visual, dict):
        errors.append("visual must be an object")
    else:
        enum_fields = {
            "direction": DIRECTIONS,
            "density": DENSITIES,
            "motion": MOTIONS,
            "media_intensity": MEDIA_LEVELS,
        }
        for field, allowed in enum_fields.items():
            if visual.get(field) not in allowed:
                errors.append(f"visual.{field} must be one of: " + ", ".join(sorted(allowed)))
        palette = visual.get("palette_preference")
        if palette is not None and not isinstance(palette, str):
            errors.append("visual.palette_preference must be a string or null")

    delivery = brief.get("delivery")
    if not isinstance(delivery, dict):
        errors.append("delivery must be an object")
    else:
        if delivery.get("format") != "html":
            errors.append('delivery.format must currently be "html"')
        if delivery.get("aspect_ratio") != "16:9":
            errors.append('delivery.aspect_ratio must currently be "16:9"')

    production = brief.get("production")
    if production is not None:
        if not isinstance(production, dict):
            errors.append("production must be an object when provided")
        else:
            if production.get("profile", "balanced") not in PRODUCTION_PROFILES:
                errors.append("production.profile must be fast, balanced, or premium")
            for field in ("ai_image_budget", "web_image_target"):
                value = production.get(field)
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 12
                ):
                    errors.append(f"production.{field} must be an integer from 0 to 12")

    for field in ("assumptions", "open_questions"):
        if not _string_list(brief.get(field)):
            errors.append(f"{field} must be an array of non-empty strings")

    if not isinstance(brief.get("confirmed"), bool):
        errors.append("confirmed must be a boolean")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a liquid-glass-slides brief.json file.")
    parser.add_argument("brief", type=Path, help="Path to brief.json")
    args = parser.parse_args()

    try:
        with args.brief.open("r", encoding="utf-8") as handle:
            brief = json.load(handle)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.brief}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return 2

    errors = validate_brief(brief)
    if errors:
        print(f"INVALID: {args.brief}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"VALID: {args.brief}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
