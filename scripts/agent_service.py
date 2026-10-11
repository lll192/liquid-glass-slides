#!/usr/bin/env python3
"""Shared agent-service boundary used by MCP and HTTP adapters."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

try:
    import slides
    from source_web_images import SourceError, source_images
except ImportError:  # pragma: no cover
    from scripts import slides
    from scripts.source_web_images import SourceError, source_images


class ServiceError(ValueError):
    """A client supplied invalid service arguments."""


class AgentService:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        if not self.workspace.is_dir():
            raise ServiceError(f"workspace is not a directory: {self.workspace}")

    def path(self, value: Any, field: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ServiceError(f"{field} must be a non-empty path string")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise ServiceError(f"{field} must stay inside workspace: {self.workspace}") from exc
        return resolved

    def inventory(self, limit: int = 500) -> dict[str, Any]:
        """Return a bounded, deterministic inventory for the local production console."""
        ignored = {".git", ".venv", "node_modules", "__pycache__"}
        json_files: list[dict[str, str]] = []
        decks: list[dict[str, str]] = []
        truncated = False
        seen = 0
        for root, directories, files in os.walk(self.workspace):
            directories[:] = sorted(
                name for name in directories
                if name not in ignored and not name.startswith(".")
            )
            for name in sorted(files):
                path = Path(root) / name
                suffix = path.suffix.lower()
                if suffix not in {".json", ".html"}:
                    continue
                seen += 1
                if seen > limit:
                    truncated = True
                    break
                relative = path.relative_to(self.workspace).as_posix()
                if suffix == ".html":
                    decks.append({
                        "path": relative, "name": path.stem, "kind": "deck",
                        "modified": int(path.stat().st_mtime),
                    })
                    continue
                kind = "json"
                try:
                    if path.stat().st_size <= 1024 * 1024:
                        value = json.loads(path.read_text(encoding="utf-8"))
                        if isinstance(value, dict):
                            if isinstance(value.get("slides"), list):
                                if value.get("schema_version") == "2.0" and value.get("deck_id"):
                                    kind = "outline"
                                elif value.get("slides") and isinstance(value["slides"][0], dict) and "planned_type" in value["slides"][0]:
                                    kind = "visual-plan"
                            elif "pipeline_version" in value and "stages" in value:
                                kind = "pipeline-state"
                            elif "sources" in value and "processing" in value:
                                kind = "source-manifest"
                            elif isinstance(value.get("assets"), list) and "reviewed" in value:
                                kind = "media-manifest"
                            elif isinstance(value.get("requests"), list) and value.get("deck_id"):
                                kind = "media-plan"
                            elif "content" in value and "audience" in value:
                                kind = "brief"
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    kind = "json"
                json_files.append({"path": relative, "name": path.stem, "kind": kind})
            if truncated:
                break
        return {
            "workspace": str(self.workspace),
            "files": json_files,
            "decks": decks,
            "truncated": truncated,
        }

    def _read_object(self, path: Path, field: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ServiceError(f"{field} was not found: {path}") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ServiceError(f"{field} is not readable JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ServiceError(f"{field} must contain a JSON object")
        return value

    def _workspace_relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.workspace).as_posix()

    @staticmethod
    def _content_fields(slide: dict[str, Any]) -> list[dict[str, Any]]:
        """Describe visible slide copy without exposing the raw outline structure."""
        labels = {
            "eyebrow": "页眉小标题", "subtitle": "页面副标题", "caption": "补充说明",
            "quote": "引用文字", "by": "引用署名", "center": "中心文字",
            "left_title": "左侧标题", "right_title": "右侧标题",
            "left": "左栏内容", "right": "右栏内容", "items": "页面内容",
            "left_items": "左侧内容", "right_items": "右侧内容", "contacts": "结尾信息",
        }
        fields: list[dict[str, Any]] = []
        for key, label in labels.items():
            value = slide.get(key)
            if isinstance(value, str):
                fields.append({
                    "key": key, "label": label,
                    "type": "html" if re.search(r"<[^>]+>", value) else "text",
                    "value": value,
                })
            elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                preferred = ["year", "icon", "label", "head", "text", "desc"]
                columns = [name for name in preferred if any(name in item for item in value)]
                if not columns:
                    continue
                lines = ["｜".join(str(item.get(name, "")) for name in columns) for item in value]
                fields.append({
                    "key": key, "label": label, "type": "list", "columns": columns,
                    "value": "\n".join(lines),
                    "hint": "每行一项；同一行的不同部分用 ｜ 分隔。",
                })
        return fields

    @staticmethod
    def _image_search_query(query: str) -> str:
        """Turn common Chinese visual phrases into Openverse-friendly English queries."""
        if not re.search(r"[\u3400-\u9fff]", query):
            return query
        replacements = [
            ("一杯摆在桌子上的咖啡", "coffee cup on table"),
            ("摆在桌子上的咖啡", "coffee cup on table"),
            ("桌子上的咖啡", "coffee cup on table"),
            ("摆在桌子上", "on table"), ("放在桌子上", "on table"),
            ("桌子上", "on table"), ("桌面上", "on table"),
            ("星巴克", "Starbucks"), ("一杯", "cup"),
            ("一杯咖啡", "coffee cup"), ("咖啡杯", "coffee cup"),
            ("咖啡", "coffee"), ("桌子", "table"), ("桌上", "on table"),
            ("白人老男人", "white elderly man"), ("老男人", "elderly man"),
            ("老年男人", "elderly man"), ("老年女人", "elderly woman"),
            ("白人", "white"), ("老人", "elderly person"), ("男人", "man"),
            ("女人", "woman"), ("人物", "person"), ("优雅", "elegant"),
            ("肖像", "portrait"), ("真实", "realistic"), ("照片", "photograph"),
            ("北欧", "Nordic"), ("冬日", "winter"), ("街道", "street"),
            ("房屋", "house"), ("读书会", "book club"), ("阅读", "reading"),
            ("书籍", "books"), ("书", "book"), ("猫", "cat"),
            ("修理", "repair"), ("工具", "tools"), ("社区", "community"),
            ("邻居", "neighbors"), ("温暖", "warm"), ("悲伤", "sad"),
        ]
        translated = query
        for chinese, english in replacements:
            translated = translated.replace(chinese, f" {english} ")
        translated = re.sub(r"[\u3400-\u9fff]+", " ", translated)
        translated = re.sub(r"\s+", " ", translated).strip()
        person_terms = {"person", "man", "woman", "elderly", "portrait"}
        if person_terms & set(translated.lower().split()):
            return f"{translated} portrait photograph"
        # Never turn an unrecognised Chinese request into a generic portrait.
        # A clear failure is safer than silently attaching an unrelated person.
        return translated

    @classmethod
    def _image_search_queries(cls, query: str) -> list[str]:
        exact = cls._image_search_query(query)
        tokens = exact.split()
        modifiers = {
            "white", "elegant", "realistic", "photograph", "photo", "editorial",
            "warm", "sad", "Nordic",
        }
        is_portrait = "portrait" in tokens
        subject = [token for token in tokens if token not in modifiers and token != "portrait"]
        candidates = [exact]
        if subject:
            if is_portrait:
                candidates.append(" ".join(subject + ["portrait"]))
            candidates.append(" ".join(subject))
        return list(dict.fromkeys(candidate for candidate in candidates if candidate.strip()))

    def _apply_media_to_outline(
        self,
        manifest_path: Path,
        manifest: dict[str, Any],
        outline_path: Path,
        removed_assets: list[dict[str, Any]],
    ) -> list[str]:
        """Materialize reviewed media choices into the fields consumed by the builder."""
        outline = self._read_object(outline_path, "outline")
        if outline.get("deck_id") != manifest.get("deck_id"):
            raise ServiceError("manifest deck_id does not match outline deck_id")
        slide_items = outline.get("slides")
        if not isinstance(slide_items, list):
            raise ServiceError("outline must contain a slides array")
        slide_by_id = {
            str(slide.get("slide_id")): slide for slide in slide_items
            if isinstance(slide, dict) and slide.get("slide_id")
        }

        def outline_image_path(asset: dict[str, Any]) -> str:
            local = asset.get("local_path")
            if not isinstance(local, str) or not local:
                raise ServiceError("media asset local_path must be a non-empty string")
            source = (manifest_path.parent / local).resolve()
            try:
                source.relative_to(self.workspace)
            except ValueError as exc:
                raise ServiceError("media asset must stay inside workspace") from exc
            return Path(os.path.relpath(source, outline_path.parent)).as_posix()

        image_fields = {
            "hero": ("hero", "hero_alt"),
            "background": ("background_image", "background_alt"),
            "decorative": ("decorative_image", "decorative_alt"),
        }
        image_metadata = {
            "hero": ("hero_alt", "hero_mode", "hero_fit", "hero_position"),
            "image": ("alt",),
            "support_image": ("support_alt", "support_fit", "support_position", "support_side"),
            "background_image": ("background_alt", "background_position"),
            "decorative_image": ("decorative_alt", "decorative_side"),
        }
        changed: set[str] = set()
        for asset in removed_assets:
            try:
                previous_path = outline_image_path(asset)
            except ServiceError:
                continue
            for slide_id in asset.get("slide_ids", []):
                slide = slide_by_id.get(str(slide_id))
                if not slide:
                    continue
                for field in ("hero", "image", "support_image", "background_image", "decorative_image"):
                    if slide.get(field) == previous_path:
                        slide.pop(field, None)
                        alt_field = {
                            "hero": "hero_alt", "image": "alt", "support_image": "support_alt",
                            "background_image": "background_alt", "decorative_image": "decorative_alt",
                        }[field]
                        slide.pop(alt_field, None)
                        changed.add(str(slide_id))

        for asset in manifest.get("assets", []):
            if not isinstance(asset, dict):
                continue
            if asset.get("selected", True) is False:
                continue
            image_path = outline_image_path(asset)
            role = str(asset.get("role", "content"))
            alt = str(asset.get("alt", ""))
            for slide_id in asset.get("slide_ids", []):
                slide = slide_by_id.get(str(slide_id))
                if not slide:
                    continue
                if asset.get("preserve_existing") and any(
                    slide.get(existing_field) == image_path
                    for existing_field in image_metadata
                ):
                    continue
                if role in image_fields:
                    field, alt_field = image_fields[role]
                elif slide.get("layout") == "cover":
                    field, alt_field = "hero", "hero_alt"
                elif slide.get("layout") in {"image-frame", "object-float"}:
                    field, alt_field = "image", "alt"
                else:
                    field, alt_field = "support_image", "support_alt"
                # A reviewed asset has exactly one display mode on a slide. This
                # removes stale slots left by older manifests, preventing the same
                # photo from appearing as both a background and a side image.
                for previous_field, metadata_fields in image_metadata.items():
                    slide.pop(previous_field, None)
                    for metadata_field in metadata_fields:
                        slide.pop(metadata_field, None)
                slide[field] = image_path
                slide[alt_field] = alt
                focal = str(asset.get("focal_point", "50% 50%"))
                fit = str(asset.get("fit", "cover"))
                if field == "background_image":
                    slide["background_position"] = focal
                elif field == "hero":
                    slide["hero_mode"] = "frame" if asset.get("origin") == "web" else slide.get("hero_mode", "auto")
                    slide["hero_fit"] = fit if fit in {"contain", "cover"} else "cover"
                    slide["hero_position"] = focal
                elif field == "support_image":
                    slide["support_fit"] = fit if fit in {"contain", "cover"} else "cover"
                    slide["support_position"] = focal
                changed.add(str(slide_id))

        errors = slides.validate_outline(outline)
        if errors:
            raise ServiceError("media application made outline invalid: " + "; ".join(errors))
        temporary = outline_path.with_suffix(outline_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(outline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(outline_path)
        return sorted(changed)

    def _outline_media_assets(
        self,
        outline: dict[str, Any],
        outline_path: Path,
        manifest_path: Path | None,
        known_assets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Recover images used by slides but missing from the selected media library."""
        known_paths: set[Path] = set()
        used_ids = {
            str(asset.get("asset_id")) for asset in known_assets
            if isinstance(asset, dict) and asset.get("asset_id")
        }
        if manifest_path:
            for asset in known_assets:
                local = asset.get("local_path") if isinstance(asset, dict) else None
                if isinstance(local, str) and local:
                    known_paths.add((manifest_path.parent / local).resolve())
        field_roles = {
            "hero": ("hero", "hero_alt"),
            "image": ("content", "alt"),
            "support_image": ("content", "support_alt"),
            "background_image": ("background", "background_alt"),
            "decorative_image": ("decorative", "decorative_alt"),
        }
        recovered: list[dict[str, Any]] = []
        for slide in outline.get("slides", []):
            if not isinstance(slide, dict):
                continue
            slide_id = str(slide.get("slide_id", "slide"))
            for field, (role, alt_field) in field_roles.items():
                value = slide.get(field)
                if not isinstance(value, str) or not value.strip():
                    continue
                source = (outline_path.parent / value).resolve()
                try:
                    source.relative_to(self.workspace)
                except ValueError:
                    continue
                if source in known_paths or not source.is_file():
                    continue
                stem = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-") or "image"
                suffix = re.sub(r"[^a-z0-9]+", "-", field.lower()).strip("-")
                asset_id = f"{stem}-{suffix}"[:64].rstrip("-")
                counter = 2
                base_id = asset_id
                while asset_id in used_ids:
                    asset_id = f"{base_id[:60]}-{counter}"
                    counter += 1
                used_ids.add(asset_id)
                relative_base = manifest_path.parent if manifest_path else outline_path.parent
                recovered.append({
                    "asset_id": asset_id,
                    "origin": "project-asset",
                    "role": role,
                    "local_path": Path(os.path.relpath(source, relative_base)).as_posix(),
                    "slide_ids": [slide_id],
                    "alt": str(slide.get(alt_field) or source.stem.replace("-", " ")),
                    "fit": "cover",
                    "focal_point": str(slide.get(
                        "background_position" if field == "background_image" else
                        "support_position" if field == "support_image" else "hero_position",
                        "50% 50%",
                    )),
                    "selected": True,
                    "preserve_existing": True,
                    "notes": "已从当前演示页面恢复到图片库",
                })
                known_paths.add(source)
        return recovered

    def inspect_project(self, outline_value: Any, manifest_value: Any = None) -> dict[str, Any]:
        """Return a bounded, UI-ready view of one deck project."""
        outline_path = self.path(outline_value, "outline")
        outline = self._read_object(outline_path, "outline")
        if not isinstance(outline.get("slides"), list):
            raise ServiceError("outline must contain a slides array")
        deck_id = str(outline.get("deck_id") or outline_path.stem)

        manifests: list[tuple[Path, dict[str, Any]]] = []
        reports: dict[str, dict[str, Any]] = {}
        report_suffixes = {
            ".qa-report.json": "qa",
            ".visual-plan.json": "visual_plan",
            ".director-report.json": "director",
            ".pipeline-state.json": "pipeline",
        }
        for path in self.workspace.rglob("*.json"):
            if any(part.startswith(".") or part in {".git", ".venv", "node_modules", "__pycache__"}
                   for part in path.relative_to(self.workspace).parts[:-1]):
                continue
            try:
                if path.stat().st_size > 2 * 1024 * 1024:
                    continue
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(value, dict) or value.get("deck_id") != deck_id:
                continue
            if isinstance(value.get("assets"), list) and "reviewed" in value:
                manifests.append((path, value))
            for suffix, name in report_suffixes.items():
                if path.name.endswith(suffix):
                    current = reports.get(name)
                    if current is None or path.stat().st_mtime > current["mtime"]:
                        reports[name] = {
                            "path": self._workspace_relative(path),
                            "mtime": path.stat().st_mtime,
                            "value": value,
                        }

        manifests.sort(key=lambda item: (
            bool(item[1].get("reviewed")),
            item[0].name == "media-manifest.json",
            item[0].stat().st_mtime,
        ), reverse=True)
        if manifest_value:
            requested_manifest = self.path(manifest_value, "mediaManifest")
            requested_value = self._read_object(requested_manifest, "mediaManifest")
            if requested_value.get("deck_id") != deck_id:
                raise ServiceError("mediaManifest deck_id does not match the outline")
            manifest_path, manifest = requested_manifest, requested_value
        else:
            manifest_path, manifest = manifests[0] if manifests else (None, {"assets": [], "reviewed": False})
        active_paths: set[Path] = set()
        for slide in outline.get("slides", []):
            if not isinstance(slide, dict):
                continue
            for field in ("hero", "image", "support_image", "background_image", "decorative_image"):
                value = slide.get(field)
                if isinstance(value, str) and value.strip():
                    active_paths.add((outline_path.parent / value).resolve())

        manifest_assets = [asset for asset in manifest.get("assets", []) if isinstance(asset, dict)]
        manifest_assets.extend(
            self._outline_media_assets(outline, outline_path, manifest_path, manifest_assets)
        )
        assets: list[dict[str, Any]] = []
        for asset in manifest_assets:
            item = dict(asset)
            local_path = item.get("local_path")
            if manifest_path and isinstance(local_path, str):
                resolved = (manifest_path.parent / local_path).resolve()
                try:
                    resolved.relative_to(self.workspace)
                    if resolved.is_file():
                        item["asset_path"] = self._workspace_relative(resolved)
                    item["in_use"] = resolved in active_paths
                except ValueError:
                    pass
            item["selected"] = item.get("selected", item.get("in_use", False))
            assets.append(item)

        image_fields = {"hero", "image", "background_image", "decorative_image", "support_image"}
        meaningful_layouts = {"chart", "data-table", "process-flow", "concept-map", "timeline", "comparison"}
        slides: list[dict[str, Any]] = []
        meaningful = notes = transitions = 0
        for index, slide in enumerate(outline["slides"]):
            if not isinstance(slide, dict):
                continue
            visual_type = "text"
            if slide.get("chart"):
                visual_type = "chart"
            elif any(slide.get(field) for field in image_fields):
                visual_type = "image"
            elif slide.get("layout") in meaningful_layouts:
                visual_type = str(slide.get("layout"))
            planned = slide.get("visual_plan") if isinstance(slide.get("visual_plan"), dict) else {}
            has_meaningful = visual_type != "text" or planned.get("priority") == "required"
            meaningful += int(has_meaningful)
            notes += int(bool(slide.get("speaker_notes")))
            transitions += int(bool(slide.get("transition")))
            slides.append({
                "order": index + 1,
                "slide_id": slide.get("slide_id", f"slide-{index + 1}"),
                "title": slide.get("title") or slide.get("quote") or "未命名页面",
                "layout": slide.get("layout", "unknown"),
                "story_role": slide.get("story_role", "auto"),
                "emotion": slide.get("emotion", "auto"),
                "main_point": slide.get("main_point", ""),
                "transition": slide.get("transition", ""),
                "speaker_notes": slide.get("speaker_notes", ""),
                "content_fields": self._content_fields(slide),
                "visual_type": visual_type,
                "visual_purpose": planned.get("purpose", ""),
                "visual_source": planned.get("source", ""),
                "meaningful_visual": has_meaningful,
            })

        slide_count = len(slides)
        web_assets = sum(asset.get("origin") == "web" for asset in assets)
        ai_assets = sum(asset.get("origin") == "ai-generated" for asset in assets)
        return {
            "deck": {
                "deck_id": deck_id,
                "title": outline.get("title", outline_path.stem),
                "lang": outline.get("lang", "zh-CN"),
                "outline": self._workspace_relative(outline_path),
                "slides": slide_count,
            },
            "metrics": {
                "visual_coverage": round(meaningful / slide_count * 100) if slide_count else 0,
                "speaker_notes_coverage": round(notes / slide_count * 100) if slide_count else 0,
                "transition_coverage": round(transitions / max(slide_count - 1, 1) * 100) if slide_count else 0,
                "web_assets": web_assets,
                "ai_assets": ai_assets,
            },
            "slides": slides,
            "media": {
                "manifest": self._workspace_relative(manifest_path) if manifest_path else "",
                "reviewed": bool(manifest.get("reviewed")),
                "assets": assets,
            },
            "reports": {
                name: {"path": report["path"], "data": report["value"]}
                for name, report in reports.items()
            },
        }

    def invoke(self, operation: str, arguments: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(arguments, dict):
            raise ServiceError("arguments must be an object")
        if operation == "doctor":
            return slides.command_doctor(argparse.Namespace(json=True))
        if operation == "inspect-project":
            project = self.inspect_project(arguments.get("outline"), arguments.get("mediaManifest"))
            return 0, {
                "api_version": "1.0", "command": "inspect-project", "ok": True,
                "message": "project inspected", "data": project, "errors": [], "warnings": [],
            }
        if operation == "validate":
            kind = arguments.get("kind", "auto")
            if kind not in {"auto", "outline", "brief", "source-manifest", "media-manifest"}:
                raise ServiceError(
                    "kind must be auto, outline, brief, source-manifest, or media-manifest"
                )
            return slides.command_validate(argparse.Namespace(
                json=True, input=self.path(arguments.get("path"), "path"), kind=kind,
            ))
        if operation == "build":
            return slides.command_build(argparse.Namespace(
                json=True,
                outline=self.path(arguments.get("outline"), "outline"),
                out=self.path(arguments.get("output"), "output"),
                assets=None,
                templates=None,
            ))
        if operation == "source-images":
            return slides.command_source_images(argparse.Namespace(
                json=True,
                plan=self.path(arguments.get("plan"), "plan"),
                project_dir=self.path(arguments.get("projectDir", "."), "projectDir"),
                manifest=self.path(arguments.get("manifest"), "manifest"),
                reviewed=bool(arguments.get("reviewed", False)),
                workers=int(arguments.get("workers", 4)),
            ))
        if operation == "add-media":
            manifest_path = self.path(arguments.get("manifest"), "manifest")
            manifest = self._read_object(manifest_path, "manifest")
            query = str(arguments.get("query", "")).strip()
            role = str(arguments.get("role", "content")).strip()
            slide_id = str(arguments.get("slideId", "")).strip()
            if not query:
                raise ServiceError("query must be a non-empty string")
            search_queries = self._image_search_queries(query)
            if not search_queries:
                raise ServiceError("暂时无法理解这个图片关键词，请写清主体、场景和动作")
            if role not in {"content", "background", "decorative", "hero"}:
                raise ServiceError("role must be content, background, decorative, or hero")
            if not slide_id:
                raise ServiceError("slideId must be a non-empty string")
            slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:28] or "image"
            asset_id = f"{slug}-{uuid.uuid4().hex[:7]}"
            plan = {
                "deck_id": manifest.get("deck_id"), "image_dir": "images/web",
                "requests": [{
                    "asset_id": asset_id, "query": search_queries[0], "role": role,
                    "slide_ids": [slide_id], "alt": query, "fit": "cover",
                    "focal_point": "50% 50%",
                }],
            }
            temp_plan: Path | None = None
            temp_manifest: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", suffix=".json", prefix="media-plan-",
                    dir=self.workspace, delete=False,
                ) as handle:
                    temp_plan = Path(handle.name)
                temp_manifest = self.workspace / f".media-extra-{uuid.uuid4().hex}.json"
                added = None
                last_error: Exception | None = None
                used_query = search_queries[0]
                for candidate_query in search_queries:
                    plan["requests"][0]["query"] = candidate_query
                    temp_plan.write_text(
                        json.dumps(plan, ensure_ascii=False), encoding="utf-8"
                    )
                    try:
                        added = source_images(
                            temp_plan, self.workspace, temp_manifest, reviewed=False, workers=1
                        )
                        used_query = candidate_query
                        break
                    except (OSError, ValueError, json.JSONDecodeError, SourceError) as exc:
                        last_error = exc
                if added is None:
                    raise ServiceError(
                        "没有找到合适且许可清晰的图片，请换一个主体更明确的关键词"
                    ) from last_error
                current_assets = manifest.get("assets")
                if not isinstance(current_assets, list):
                    raise ServiceError("manifest assets must be an array")
                current_assets.extend(added.get("assets", []))
                manifest["reviewed"] = False
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            finally:
                for temporary in (temp_plan, temp_manifest):
                    if temporary:
                        temporary.unlink(missing_ok=True)
            return 0, {
                "api_version": "1.0", "command": "add-media", "ok": True,
                "message": "image added for review", "errors": [], "warnings": [],
                "data": {"manifest": str(manifest_path), "asset_id": asset_id,
                         "assets": len(manifest.get("assets", [])), "reviewed": False,
                         "search_query": used_query},
            }
        if operation == "review-media":
            manifest_path = self.path(arguments.get("manifest"), "manifest")
            manifest = self._read_object(manifest_path, "manifest")
            assets = manifest.get("assets")
            if not isinstance(assets, list):
                raise ServiceError("manifest assets must be an array")
            outline_value = arguments.get("outline")
            outline_path: Path | None = None
            if outline_value:
                outline_path = self.path(outline_value, "outline")
                outline = self._read_object(outline_path, "outline")
                assets.extend(
                    self._outline_media_assets(outline, outline_path, manifest_path, assets)
                )
            original_assets = list(assets)
            selected = arguments.get("selectedAssetIds")
            if selected is not None:
                if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
                    raise ServiceError("selectedAssetIds must be a string array")
                selected_ids = set(selected)
                known_ids = {str(asset.get("asset_id")) for asset in assets}
                missing = selected_ids - known_ids
                if missing:
                    raise ServiceError("unknown asset ids: " + ", ".join(sorted(missing)))
                for asset in assets:
                    if isinstance(asset, dict):
                        asset["selected"] = str(asset.get("asset_id")) in selected_ids
                manifest["assets"] = assets
            manifest["reviewed"] = True
            errors = slides.validate_media_manifest(manifest)
            if errors:
                raise ServiceError("invalid media manifest: " + "; ".join(errors))
            temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(manifest_path)
            applied_slides: list[str] = []
            kept_ids = {
                str(asset.get("asset_id")) for asset in assets
                if isinstance(asset, dict) and asset.get("selected", True)
            }
            if outline_path:
                removed_assets = [
                    asset for asset in original_assets
                    if isinstance(asset, dict) and str(asset.get("asset_id")) not in kept_ids
                ]
                applied_slides = self._apply_media_to_outline(
                    manifest_path, manifest, outline_path, removed_assets
                )
            return 0, {
                "api_version": "1.0", "command": "review-media", "ok": True,
                "message": "media selection approved", "errors": [], "warnings": [],
                "data": {"manifest": str(manifest_path), "assets": len(kept_ids),
                         "library_assets": len(assets), "reviewed": True,
                         "applied_slides": applied_slides},
            }
        if operation == "update-slide":
            outline_path = self.path(arguments.get("outline"), "outline")
            outline = self._read_object(outline_path, "outline")
            slide_id = arguments.get("slideId")
            patch = arguments.get("patch")
            if not isinstance(slide_id, str) or not slide_id:
                raise ServiceError("slideId must be a non-empty string")
            if not isinstance(patch, dict) or not patch:
                raise ServiceError("patch must be a non-empty object")
            string_fields = {
                "title", "main_point", "transition", "speaker_notes", "eyebrow", "subtitle",
                "caption", "quote", "by", "center", "left_title", "right_title", "left", "right",
            }
            list_fields = {"items", "left_items", "right_items", "contacts"}
            allowed = string_fields | list_fields
            unknown = set(patch) - allowed
            if unknown:
                raise ServiceError("unsupported slide fields: " + ", ".join(sorted(unknown)))
            if any(not isinstance(patch[key], str) for key in patch if key in string_fields):
                raise ServiceError("editable text fields must be strings")
            for key in set(patch) & list_fields:
                value = patch[key]
                if not isinstance(value, list) or not all(
                    isinstance(item, dict) and all(
                        isinstance(name, str) and isinstance(text, str)
                        for name, text in item.items()
                    ) for item in value
                ):
                    raise ServiceError(f"{key} must be a list of text objects")
            slide = next((item for item in outline.get("slides", []) if item.get("slide_id") == slide_id), None)
            if slide is None:
                raise ServiceError(f"slideId was not found: {slide_id}")
            slide.update(patch)
            errors = slides.validate_outline(outline)
            if errors:
                raise ServiceError("updated outline is invalid: " + "; ".join(errors))
            temporary = outline_path.with_suffix(outline_path.suffix + ".tmp")
            temporary.write_text(json.dumps(outline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(outline_path)
            return 0, {
                "api_version": "1.0", "command": "update-slide", "ok": True,
                "message": "slide updated", "errors": [], "warnings": [],
                "data": {"outline": str(outline_path), "slide_id": slide_id, "fields": sorted(patch)},
            }
        if operation == "run":
            return slides.command_run(argparse.Namespace(
                json=True,
                outline=self.path(arguments.get("outline"), "outline"),
                out=self.path(arguments.get("output"), "output"),
                brief=self.path(arguments["brief"], "brief") if arguments.get("brief") else None,
                source_manifest=(
                    self.path(arguments["sourceManifest"], "sourceManifest")
                    if arguments.get("sourceManifest") else None
                ),
                media_manifest=(
                    self.path(arguments["mediaManifest"], "mediaManifest")
                    if arguments.get("mediaManifest") else None
                ),
                state=self.path(arguments["state"], "state") if arguments.get("state") else None,
                assets=None,
                templates=None,
            ))
        if operation == "status":
            return slides.command_status(argparse.Namespace(
                json=True, state=self.path(arguments.get("state"), "state")
            ))
        if operation == "mark-exported":
            return slides.command_mark_exported(argparse.Namespace(
                json=True,
                state=self.path(arguments.get("state"), "state"),
                message=arguments.get("message"),
            ))
        raise ServiceError(f"unknown operation: {operation}")
