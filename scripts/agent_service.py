#!/usr/bin/env python3
"""Shared agent-service boundary used by MCP and HTTP adapters."""

from __future__ import annotations

import argparse
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

    def invoke(self, operation: str, arguments: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(arguments, dict):
            raise ServiceError("arguments must be an object")
        if operation == "doctor":
            return slides.command_doctor(argparse.Namespace(json=True))
        if operation == "validate":
            kind = arguments.get("kind", "auto")
            if kind not in {"auto", "outline", "brief", "source-manifest"}:
                raise ServiceError("kind must be auto, outline, brief, or source-manifest")
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
