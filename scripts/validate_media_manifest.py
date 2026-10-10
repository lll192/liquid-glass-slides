#!/usr/bin/env python3
"""Validate sourced, generated, and user-provided presentation media metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse


ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
ORIGINS = {"web", "ai-generated", "user-provided", "project-asset"}
ROLES = {"hero", "content", "background", "decorative", "reference"}
FITS = {"contain", "cover"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _https(value: Any) -> bool:
    if not _text(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _safe_relative_path(value: Any) -> bool:
    if not _text(value):
        return False
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return not path.is_absolute() and ".." not in path.parts and ":" not in path.parts[0]


def validate_media_manifest(manifest: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["root must be a JSON object"]
    if manifest.get("schema_version") != "1.0":
        errors.append('schema_version must be "1.0"')
    if not _text(manifest.get("deck_id")):
        errors.append("deck_id must be a non-empty string")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        errors.append("assets must be an array")
        return errors
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        asset_id = asset.get("asset_id")
        if not _text(asset_id) or not ID_RE.fullmatch(asset_id):
            errors.append(f"{prefix}.asset_id must use 2-64 lowercase letters, numbers, or hyphens")
        elif asset_id in seen:
            errors.append(f"{prefix}.asset_id duplicates {asset_id}")
        else:
            seen.add(asset_id)
        if asset.get("origin") not in ORIGINS:
            errors.append(f"{prefix}.origin must be one of: " + ", ".join(sorted(ORIGINS)))
        if asset.get("role") not in ROLES:
            errors.append(f"{prefix}.role must be one of: " + ", ".join(sorted(ROLES)))
        if not _safe_relative_path(asset.get("local_path")):
            errors.append(f"{prefix}.local_path must be a safe relative path")
        slides = asset.get("slide_ids")
        if not isinstance(slides, list) or not slides or not all(_text(item) for item in slides):
            errors.append(f"{prefix}.slide_ids must be a non-empty string array")
        if not _text(asset.get("alt")):
            errors.append(f"{prefix}.alt must be a non-empty string")
        if asset.get("fit", "contain") not in FITS:
            errors.append(f"{prefix}.fit must be contain or cover")
        position = asset.get("focal_point", "50% 50%")
        if not isinstance(position, str) or not re.fullmatch(r"\d{1,3}%\s+\d{1,3}%", position.strip()):
            errors.append(f"{prefix}.focal_point must look like 50% 50%")
        if asset.get("origin") == "web":
            for field in ("source_url", "license_url"):
                if not _https(asset.get(field)):
                    errors.append(f"{prefix}.{field} must be an https URL for web assets")
            for field in ("license", "author"):
                if not _text(asset.get(field)):
                    errors.append(f"{prefix}.{field} is required for web assets")
    if not isinstance(manifest.get("reviewed"), bool):
        errors.append("reviewed must be a boolean")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate media-manifest.json")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.manifest}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            file=sys.stderr,
        )
        return 2
    errors = validate_media_manifest(manifest)
    if errors:
        print(f"INVALID: {args.manifest}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"VALID: {args.manifest} ({len(manifest['assets'])} assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
