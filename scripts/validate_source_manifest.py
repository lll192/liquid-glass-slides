#!/usr/bin/env python3
"""Validate a liquid-glass-slides source manifest using only the stdlib."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MODES = {"supplied", "assisted"}
PROCESSING = {"preserve", "light-edit", "restructure"}
ROLES = {"primary", "supporting", "data", "visual"}
PURPOSES = {"must-use", "reference", "evidence", "visual"}
STATUSES = {"available", "missing", "unreadable"}
COVERAGE = {"provided", "partial", "missing"}
VISUAL_TREATMENTS = {"evidence", "decorative"}
VISUAL_FITS = {"contain", "cover", "float", "no-crop"}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def validate_manifest(manifest: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["root must be a JSON object"]

    if manifest.get("schema_version") != "1.0":
        errors.append('schema_version must be "1.0"')

    mode = manifest.get("mode")
    if mode not in MODES:
        errors.append("mode must be one of: " + ", ".join(sorted(MODES)))
    if manifest.get("processing") not in PROCESSING:
        errors.append("processing must be one of: " + ", ".join(sorted(PROCESSING)))

    sources = manifest.get("sources")
    source_ids: set[str] = set()
    primary_count = 0
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
        sources = []

    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("id")
        if not _nonempty_string(source_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif source_id in source_ids:
            errors.append(f"{prefix}.id duplicates {source_id}")
        else:
            source_ids.add(source_id)
        if not _nonempty_string(source.get("path")):
            errors.append(f"{prefix}.path must be a non-empty string")
        role = source.get("role")
        if role not in ROLES:
            errors.append(f"{prefix}.role must be one of: " + ", ".join(sorted(ROLES)))
        elif role == "primary":
            primary_count += 1
        purpose = source.get("purpose")
        if purpose not in PURPOSES:
            errors.append(f"{prefix}.purpose must be one of: " + ", ".join(sorted(PURPOSES)))
        if not _nonempty_string(source.get("scope")):
            errors.append(f"{prefix}.scope must be a non-empty string")
        status = source.get("status")
        if status not in STATUSES:
            errors.append(f"{prefix}.status must be one of: " + ", ".join(sorted(STATUSES)))
        elif purpose in {"must-use", "evidence"} and status != "available":
            errors.append(f"{prefix} is required for the deck but is not available")
        if role == "visual":
            if purpose != "visual":
                errors.append(f"{prefix}.purpose must be visual when role is visual")
            if not _nonempty_string(source.get("intended_use")):
                errors.append(f"{prefix}.intended_use must be a non-empty string")
            if source.get("treatment") not in VISUAL_TREATMENTS:
                errors.append(
                    f"{prefix}.treatment must be one of: "
                    + ", ".join(sorted(VISUAL_TREATMENTS))
                )
            if source.get("fit") not in VISUAL_FITS:
                errors.append(
                    f"{prefix}.fit must be one of: " + ", ".join(sorted(VISUAL_FITS))
                )
            for optional_field in ("caption", "credit"):
                value = source.get(optional_field)
                if value is not None and not isinstance(value, str):
                    errors.append(f"{prefix}.{optional_field} must be a string or null")

    if mode == "supplied" and primary_count != 1:
        errors.append("supplied mode requires exactly one primary source")

    for field in ("must_preserve", "ai_fill", "conflicts", "assumptions", "open_questions"):
        if not _string_list(manifest.get(field)):
            errors.append(f"{field} must be an array of non-empty strings")

    content_map = manifest.get("content_map")
    if not isinstance(content_map, list) or not content_map:
        errors.append("content_map must be a non-empty array")
        content_map = []

    for index, entry in enumerate(content_map):
        prefix = f"content_map[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not _nonempty_string(entry.get("section")):
            errors.append(f"{prefix}.section must be a non-empty string")
        coverage = entry.get("coverage")
        if coverage not in COVERAGE:
            errors.append(f"{prefix}.coverage must be one of: " + ", ".join(sorted(COVERAGE)))
        ids = entry.get("source_ids")
        if not isinstance(ids, list) or not all(_nonempty_string(item) for item in ids):
            errors.append(f"{prefix}.source_ids must be an array of non-empty strings")
            ids = []
        for source_id in ids:
            if source_id not in source_ids:
                errors.append(f"{prefix}.source_ids references unknown id {source_id}")
        if coverage in {"provided", "partial"} and not ids:
            errors.append(f"{prefix} with {coverage} coverage requires at least one source id")
        if coverage == "missing" and ids:
            errors.append(f"{prefix} with missing coverage must not reference a source id")
        if not _nonempty_string(entry.get("handling")):
            errors.append(f"{prefix}.handling must be a non-empty string")

    if not isinstance(manifest.get("confirmed"), bool):
        errors.append("confirmed must be a boolean")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a liquid-glass-slides source-manifest.json file."
    )
    parser.add_argument("manifest", type=Path, help="Path to source-manifest.json")
    args = parser.parse_args()

    try:
        with args.manifest.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.manifest}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            file=sys.stderr,
        )
        return 2

    errors = validate_manifest(manifest)
    if errors:
        print(f"INVALID: {args.manifest}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"VALID: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
