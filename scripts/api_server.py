#!/usr/bin/env python3
"""Authenticated local HTTP API for Liquid Glass Slides."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from agent_service import AgentService, ServiceError
except ImportError:  # pragma: no cover
    from scripts.agent_service import AgentService, ServiceError


API_VERSION = "1.0"
MAX_BODY_BYTES = 1024 * 1024
LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def openapi_document() -> dict[str, Any]:
    operation_schema = {
        "type": "object",
        "required": ["api_version", "command", "ok", "message", "data", "errors", "warnings"],
    }
    paths: dict[str, Any] = {
        "/health": {"get": {"summary": "Liveness check", "responses": {"200": {"description": "Healthy"}}}},
        "/v1/capabilities": {
            "get": {"summary": "Discover engine capabilities", "security": [{"bearerAuth": []}]}
        },
    }
    for name in ("validate", "build", "run", "status", "mark-exported"):
        paths[f"/v1/{name}"] = {
            "post": {
                "summary": f"Run {name}",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "responses": {
                    "200": {
                        "description": "Operation completed",
                        "content": {"application/json": {"schema": operation_schema}},
                    }
                },
            }
        }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Liquid Glass Slides API", "version": API_VERSION},
        "servers": [{"url": "http://127.0.0.1:8765"}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
    }


def _server_payload(command: str, message: str, errors: list[str]) -> dict[str, Any]:
    return {
        "api_version": API_VERSION,
        "command": command,
        "ok": False,
        "message": message,
        "data": {},
        "errors": errors,
        "warnings": [],
    }


def handler_class(service: AgentService, token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "LiquidGlassSlidesAPI/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            print("[api] " + format % args, file=sys.stderr)

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Request-Id", str(uuid.uuid4()))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            supplied = self.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            return secrets.compare_digest(supplied, expected)

        def _require_auth(self) -> bool:
            if self._authorized():
                return True
            self._send(401, _server_payload("auth", "authorization required", ["invalid bearer token"]))
            return False

        def _body(self) -> dict[str, Any]:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                raise ServiceError("Content-Type must be application/json")
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length or "0")
            except ValueError as exc:
                raise ServiceError("invalid Content-Length") from exc
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ServiceError(f"request body must be 1-{MAX_BODY_BYTES} bytes")
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ServiceError(f"invalid JSON body: {exc}") from exc
            if not isinstance(value, dict):
                raise ServiceError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, {
                    "api_version": API_VERSION,
                    "ok": True,
                    "service": "liquid-glass-slides",
                    "status": "healthy",
                })
                return
            if path == "/openapi.json":
                self._send(200, openapi_document())
                return
            if path == "/v1/capabilities":
                if not self._require_auth():
                    return
                _, payload = service.invoke("doctor", {})
                self._send(200, payload)
                return
            self._send(404, _server_payload("http", "route not found", [path]))

        def do_POST(self) -> None:
            if not self._require_auth():
                return
            path = urlparse(self.path).path
            operation = {
                "/v1/validate": "validate",
                "/v1/build": "build",
                "/v1/run": "run",
                "/v1/status": "status",
                "/v1/mark-exported": "mark-exported",
            }.get(path)
            if not operation:
                self._send(404, _server_payload("http", "route not found", [path]))
                return
            try:
                arguments = self._body()
                code, payload = service.invoke(operation, arguments)
            except ServiceError as exc:
                self._send(400, _server_payload(operation, "invalid request", [str(exc)]))
                return
            status = 200 if code == 0 else (422 if code == 1 else 400)
            self._send(status, payload)

    return Handler


def create_server(workspace: Path, host: str, port: int, token: str) -> ThreadingHTTPServer:
    service = AgentService(workspace)
    server = ThreadingHTTPServer((host, port), handler_class(service, token))
    server.daemon_threads = True
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Liquid Glass Slides authenticated HTTP API")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", help="Bearer token; generated when omitted")
    parser.add_argument(
        "--allow-remote", action="store_true",
        help="allow binding outside loopback; use only behind TLS and a trusted firewall",
    )
    args = parser.parse_args()
    if args.host not in LOCAL_HOSTS and not args.allow_remote:
        print("ERROR: non-loopback binding requires --allow-remote", file=sys.stderr)
        return 2
    if not (1 <= args.port <= 65535):
        print("ERROR: port must be between 1 and 65535", file=sys.stderr)
        return 2
    token = args.token or secrets.token_urlsafe(32)
    try:
        server = create_server(args.workspace, args.host, args.port, token)
    except (OSError, ServiceError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    host, port = server.server_address[:2]
    print(f"Liquid Glass Slides API: http://{host}:{port}", file=sys.stderr)
    print(f"Bearer token: {token}", file=sys.stderr)
    print(f"Workspace: {args.workspace.resolve()}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
