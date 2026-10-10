#!/usr/bin/env python3
"""Search Openverse for reusable real-world images and materialize a media manifest."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.openverse.org/v1/images/"
ALLOWED_LICENSES = "pdm,cc0,by,by-sa"
USER_AGENT = "liquid-glass-slides/2.7 (+https://github.com/lll192/liquid-glass-slides)"
MAX_BYTES = 18 * 1024 * 1024


class SourceError(RuntimeError):
    pass


def _get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def _choose(results: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    candidates = []
    for item in results:
        url = item.get("url") or item.get("thumbnail")
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        if not item.get("license_url") or not (item.get("creator") or item.get("attribution")):
            continue
        width = item.get("width") if isinstance(item.get("width"), int) else 0
        height = item.get("height") if isinstance(item.get("height"), int) else 0
        if width and height:
            ratio = width / max(height, 1)
            ratio_score = (
                abs(ratio - 1.78) if role == "background"
                else abs(ratio - 1.25) if role in {"content", "hero"}
                else abs(ratio - 1.0)
            )
        else:
            ratio_score = 2.0
        size_score = min(width * height, 16_000_000) / 16_000_000
        candidates.append((ratio_score - size_score * .25, item))
    return min(candidates, key=lambda pair: pair[0])[1] if candidates else None


def _download(urls: list[str], target_without_suffix: Path) -> Path:
    last_error: Exception | None = None
    for url in urls:
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
            with urlopen(request, timeout=35) as response:
                content_type = response.headers.get_content_type()
                if not content_type.startswith("image/"):
                    raise SourceError(f"download did not return an image: {content_type}")
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise SourceError("image exceeds the 18 MB download limit")
            extension = mimetypes.guess_extension(content_type) or ".jpg"
            if extension == ".jpe":
                extension = ".jpg"
            target = target_without_suffix.with_suffix(extension)
            target.write_bytes(data)
            return target
        except Exception as exc:  # try the provider thumbnail as a fallback
            last_error = exc
    raise SourceError(f"unable to download selected image: {last_error}")


def _source_one(request_item: dict[str, Any], project_dir: Path, image_dir: Path) -> dict[str, Any]:
    asset_id = str(request_item.get("asset_id", "")).strip()
    query = str(request_item.get("query", "")).strip()
    role = str(request_item.get("role", "content")).strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", asset_id):
        raise SourceError("asset_id must use lowercase letters, numbers, and hyphens")
    if not query:
        raise SourceError(f"{asset_id}: query is required")
    pinned_id = str(request_item.get("openverse_id", "")).strip()
    if pinned_id:
        selected = _get_json(API_URL + pinned_id + "/")
    else:
        params = {
            "q": query,
            "page_size": 20,
            "license": ALLOWED_LICENSES,
            "mature": "false",
        }
        payload = _get_json(API_URL + "?" + urlencode(params))
        selected = _choose(payload.get("results", []), role)
    if not selected:
        raise SourceError(f"{asset_id}: no reusable image result found for {query!r}")
    target = _download(
        [selected.get("url"), selected.get("thumbnail")], image_dir / asset_id
    )
    license_name = str(selected.get("license", "")).upper()
    version = str(selected.get("license_version", "")).strip()
    if version:
        license_name += " " + version
    creator = selected.get("creator") or selected.get("attribution") or "Unknown creator"
    return {
        "asset_id": asset_id,
        "origin": "web",
        "role": role,
        "local_path": target.relative_to(project_dir).as_posix(),
        "slide_ids": request_item.get("slide_ids", []),
        "alt": request_item.get("alt") or selected.get("title") or query,
        "fit": request_item.get("fit", "cover"),
        "focal_point": request_item.get("focal_point", "50% 50%"),
        "source_url": selected.get("foreign_landing_url") or selected.get("detail_url"),
        "download_url": selected.get("url") or selected.get("thumbnail"),
        "author": str(creator),
        "license": license_name,
        "license_url": selected.get("license_url"),
        "provider": selected.get("provider"),
        "source": selected.get("source"),
        "title": selected.get("title"),
        "query": query,
    }


def source_images(plan_path: Path, project_dir: Path, manifest_path: Path,
                  reviewed: bool = False, workers: int = 4) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    requests = plan.get("requests")
    if not isinstance(requests, list) or not requests:
        raise SourceError("plan.requests must be a non-empty array")
    if len(requests) > 12:
        raise SourceError("one sourcing run may request at most 12 images")
    project_dir = project_dir.resolve()
    image_dir = project_dir / str(plan.get("image_dir", "images/web"))
    image_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
        futures = {
            executor.submit(_source_one, item, project_dir, image_dir): item
            for item in requests
        }
        for future in as_completed(futures):
            try:
                assets.append(future.result())
            except Exception as exc:
                errors.append(str(exc))
    if errors:
        raise SourceError("; ".join(errors))
    order = {str(item.get("asset_id")): index for index, item in enumerate(requests)}
    assets.sort(key=lambda item: order.get(item["asset_id"], 999))
    manifest = {
        "schema_version": "1.0",
        "deck_id": plan.get("deck_id"),
        "reviewed": reviewed,
        "assets": assets,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Source reusable real-world images with Openverse")
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--reviewed", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    try:
        manifest = source_images(
            args.plan, args.project_dir, args.manifest, args.reviewed, args.workers
        )
    except (OSError, ValueError, json.JSONDecodeError, SourceError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps({"ok": True, "assets": len(manifest["assets"]),
                      "manifest": str(args.manifest.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
