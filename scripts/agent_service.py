#!/usr/bin/env python3
"""Shared agent-service boundary used by MCP and HTTP adapters."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    import slides
except ImportError:  # pragma: no cover
    from scripts import slides


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
                    decks.append({"path": relative, "name": path.stem, "kind": "deck"})
                    continue
                kind = "json"
                try:
                    if path.stat().st_size <= 1024 * 1024:
                        value = json.loads(path.read_text(encoding="utf-8"))
                        if isinstance(value, dict):
                            if isinstance(value.get("slides"), list):
                                kind = "outline"
                            elif "pipeline_version" in value and "stages" in value:
                                kind = "pipeline-state"
                            elif "sources" in value and "processing" in value:
                                kind = "source-manifest"
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

    def invoke(self, operation: str, arguments: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(arguments, dict):
            raise ServiceError("arguments must be an object")
        if operation == "doctor":
            return slides.command_doctor(argparse.Namespace(json=True))
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
