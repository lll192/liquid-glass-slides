#!/usr/bin/env python3
"""Zero-dependency MCP stdio server for Liquid Glass Slides."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import slides
except ImportError:  # pragma: no cover
    from scripts import slides


SERVER_NAME = "liquid-glass-slides"
SERVER_VERSION = "1.1.0"
LATEST_PROTOCOL = "2026-07-28"
LATEST_LEGACY_PROTOCOL = "2025-11-25"
LEGACY_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18", LATEST_LEGACY_PROTOCOL}
SUPPORTED_PROTOCOLS = LEGACY_PROTOCOLS | {LATEST_PROTOCOL}
SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"
PROTOCOL_META_KEY = "io.modelcontextprotocol/protocolVersion"


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


TOOLS = [
    {
        "name": "slides_doctor",
        "description": "Check the local presentation engine and discover supported capabilities.",
        "inputSchema": _schema({}),
    },
    {
        "name": "slides_validate",
        "description": "Validate an outline, design brief, or source manifest before production.",
        "inputSchema": _schema(
            {
                "path": {"type": "string", "description": "JSON path inside the MCP workspace."},
                "kind": {
                    "type": "string",
                    "enum": ["auto", "outline", "brief", "source-manifest"],
                    "default": "auto",
                },
            },
            ["path"],
        ),
    },
    {
        "name": "slides_build",
        "description": "Validate an outline and build one self-contained HTML presentation.",
        "inputSchema": _schema(
            {
                "outline": {"type": "string", "description": "Outline JSON path inside the workspace."},
                "output": {"type": "string", "description": "Destination HTML path inside the workspace."},
            },
            ["outline", "output"],
        ),
    },
    {
        "name": "slides_run",
        "description": "Run the recoverable production pipeline and emit planning, deck, QA, and state artifacts.",
        "inputSchema": _schema(
            {
                "outline": {"type": "string"},
                "output": {"type": "string"},
                "brief": {"type": "string"},
                "sourceManifest": {"type": "string"},
                "state": {"type": "string"},
            },
            ["outline", "output"],
        ),
    },
    {
        "name": "slides_status",
        "description": "Read a production pipeline state file.",
        "inputSchema": _schema(
            {"state": {"type": "string", "description": "Pipeline state JSON path."}},
            ["state"],
        ),
    },
    {
        "name": "slides_mark_exported",
        "description": "Mark a ready production job as delivered or exported.",
        "inputSchema": _schema(
            {
                "state": {"type": "string"},
                "message": {"type": "string"},
            },
            ["state"],
        ),
    },
]

RESOURCES = [
    {
        "uri": "slides://schema/deck-v2",
        "name": "Deck Protocol v2 schema",
        "description": "Machine-readable outline contract for generated presentations.",
        "mimeType": "application/schema+json",
    },
    {
        "uri": "slides://schema/agent-response-v1",
        "name": "Agent response schema",
        "description": "Stable structured response shared by CLI and MCP tools.",
        "mimeType": "application/schema+json",
    },
    {
        "uri": "slides://instructions",
        "name": "Presentation production instructions",
        "description": "Model-neutral planning, generation, and verification workflow.",
        "mimeType": "text/markdown",
    },
    {
        "uri": "slides://layouts",
        "name": "Supported layouts",
        "description": "Current semantic layout identifiers accepted by the engine.",
        "mimeType": "application/json",
    },
]


class Server:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.initialized = False

    def _modern(self, params: dict[str, Any]) -> bool:
        meta = params.get("_meta")
        return isinstance(meta, dict) and meta.get(PROTOCOL_META_KEY) == LATEST_PROTOCOL

    def _modern_result(self, result: dict[str, Any], modern: bool) -> dict[str, Any]:
        if not modern:
            return result
        value = dict(result)
        value.setdefault("_meta", {})[SERVER_INFO_META_KEY] = {
            "name": SERVER_NAME, "version": SERVER_VERSION
        }
        return value

    def _path(self, value: Any, field: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise RpcError(-32602, f"{field} must be a non-empty path string")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise RpcError(-32602, f"{field} must stay inside workspace: {self.workspace}") from exc
        return resolved

    def _invoke(self, name: str, arguments: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if name == "slides_doctor":
            return slides.command_doctor(argparse.Namespace(json=True))
        if name == "slides_validate":
            return slides.command_validate(argparse.Namespace(
                json=True,
                input=self._path(arguments.get("path"), "path"),
                kind=arguments.get("kind", "auto"),
            ))
        if name == "slides_build":
            return slides.command_build(argparse.Namespace(
                json=True,
                outline=self._path(arguments.get("outline"), "outline"),
                out=self._path(arguments.get("output"), "output"),
                assets=None,
                templates=None,
            ))
        if name == "slides_run":
            return slides.command_run(argparse.Namespace(
                json=True,
                outline=self._path(arguments.get("outline"), "outline"),
                out=self._path(arguments.get("output"), "output"),
                brief=self._path(arguments["brief"], "brief") if arguments.get("brief") else None,
                source_manifest=(
                    self._path(arguments["sourceManifest"], "sourceManifest")
                    if arguments.get("sourceManifest") else None
                ),
                state=self._path(arguments["state"], "state") if arguments.get("state") else None,
                assets=None,
                templates=None,
            ))
        if name == "slides_status":
            return slides.command_status(argparse.Namespace(
                json=True, state=self._path(arguments.get("state"), "state")
            ))
        if name == "slides_mark_exported":
            return slides.command_mark_exported(argparse.Namespace(
                json=True,
                state=self._path(arguments.get("state"), "state"),
                message=arguments.get("message"),
            ))
        raise RpcError(-32602, f"unknown tool: {name}")

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            raise RpcError(-32600, "invalid JSON-RPC request")
        method = request["method"]
        request_id = request.get("id")
        params = request.get("params") or {}
        if not isinstance(params, dict):
            raise RpcError(-32602, "params must be an object")

        modern = self._modern(params)
        if method == "server/discover":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self._modern_result({
                    "supportedVersions": [LATEST_PROTOCOL],
                    "capabilities": {"tools": {}, "resources": {}},
                    "instructions": (
                        "Build Liquid Glass HTML presentations inside the configured workspace. "
                        "Validate inputs before production and surface all errors without inventing facts."
                    ),
                    "ttlMs": 3600000,
                    "cacheScope": "public",
                }, True),
            }
        if method == "initialize":
            requested = params.get("protocolVersion")
            protocol = requested if requested in LEGACY_PROTOCOLS else LATEST_LEGACY_PROTOCOL
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": protocol,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": (
                        "Build Liquid Glass HTML presentations inside the configured workspace. "
                        "Validate inputs before production and surface all errors without inventing facts."
                    ),
                },
            }
        if method == "notifications/initialized":
            self.initialized = True
            return None
        if method == "ping":
            if modern:
                raise RpcError(-32601, "ping is not supported by protocol 2026-07-28")
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if not self.initialized and not modern:
            raise RpcError(-32002, "server has not received notifications/initialized")
        if method == "tools/list":
            result = {"tools": TOOLS}
            if modern:
                result.update({"ttlMs": 3600000, "cacheScope": "public"})
            return {
                "jsonrpc": "2.0", "id": request_id,
                "result": self._modern_result(result, modern),
            }
        if method == "resources/list":
            result = {"resources": RESOURCES}
            if modern:
                result.update({"ttlMs": 3600000, "cacheScope": "public"})
            return {
                "jsonrpc": "2.0", "id": request_id,
                "result": self._modern_result(result, modern),
            }
        if method == "resources/read":
            uri = params.get("uri")
            mapping = {
                "slides://schema/deck-v2": (
                    slides.ROOT / "references" / "deck-schema-v2.json", "application/schema+json"
                ),
                "slides://schema/agent-response-v1": (
                    slides.ROOT / "references" / "agent-response-schema-v1.json",
                    "application/schema+json",
                ),
                "slides://instructions": (
                    slides.ROOT / "references" / "INSTRUCTIONS.md", "text/markdown"
                ),
            }
            if uri == "slides://layouts":
                resource_text = json.dumps(
                    {"layouts": sorted(slides.LAYOUTS)}, ensure_ascii=False, indent=2
                )
                mime_type = "application/json"
            elif uri in mapping:
                path, mime_type = mapping[uri]
                resource_text = path.read_text(encoding="utf-8")
            else:
                raise RpcError(-32002, f"resource not found: {uri}")
            result = {
                "contents": [{"uri": uri, "mimeType": mime_type, "text": resource_text}]
            }
            if modern:
                result.update({"ttlMs": 3600000, "cacheScope": "public"})
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self._modern_result(result, modern),
            }
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise RpcError(-32602, "tools/call requires name and object arguments")
            code, payload = self._invoke(name, arguments)
            result = {
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                "structuredContent": payload,
                "isError": code != 0,
            }
            if modern:
                result["resultType"] = "complete"
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self._modern_result(result, modern),
            }
        raise RpcError(-32601, f"method not found: {method}")


def _error(request_id: Any, exc: RpcError) -> dict[str, Any]:
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.data is not None:
        error["data"] = exc.data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def serve(workspace: Path) -> int:
    server = Server(workspace)
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        request_id: Any = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise RpcError(-32600, "request must be an object")
            request_id = request.get("id")
            response = server.handle(request)
        except json.JSONDecodeError as exc:
            response = _error(None, RpcError(-32700, f"parse error: {exc.msg}"))
        except RpcError as exc:
            response = _error(request_id, exc)
        except Exception as exc:  # keep protocol stdout valid; diagnostics belong in the response
            response = _error(request_id, RpcError(-32603, "internal error", str(exc)))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Liquid Glass Slides MCP stdio server")
    parser.add_argument(
        "--workspace", type=Path, default=Path.cwd(),
        help="only files inside this directory may be read or written",
    )
    args = parser.parse_args()
    if not args.workspace.resolve().is_dir():
        print(f"ERROR: workspace is not a directory: {args.workspace}", file=sys.stderr)
        return 2
    return serve(args.workspace)


if __name__ == "__main__":
    raise SystemExit(main())
