#!/usr/bin/env python3
"""Stable agent-facing CLI for Liquid Glass Slides.

This facade keeps AI integrations on one command contract while delegating all
validation, building, and production work to the existing core modules.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import platform
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from build import build
    from pipeline import PIPELINE_VERSION, _read_json, mark_exported, run_pipeline
    from validate_brief import validate_brief
    from validate_outline import LAYOUTS, SCHEMA_VERSION, validate_outline
    from validate_source_manifest import validate_manifest
except ImportError:  # pragma: no cover
    from scripts.build import build
    from scripts.pipeline import PIPELINE_VERSION, _read_json, mark_exported, run_pipeline
    from scripts.validate_brief import validate_brief
    from scripts.validate_outline import LAYOUTS, SCHEMA_VERSION, validate_outline
    from scripts.validate_source_manifest import validate_manifest


CLI_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _result(
    command: str,
    ok: bool,
    message: str,
    *,
    data: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "api_version": CLI_VERSION,
        "command": command,
        "ok": ok,
        "message": message,
        "data": data or {},
        "errors": errors or [],
        "warnings": warnings or [],
    }


def _emit(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    stream = sys.stdout if payload["ok"] else sys.stderr
    print(("OK: " if payload["ok"] else "ERROR: ") + payload["message"], file=stream)
    for error in payload["errors"]:
        print(f"- {error}", file=stream)
    for warning in payload["warnings"]:
        print(f"WARNING: {warning}", file=stream)
    for key, value in payload["data"].items():
        if value not in (None, "", [], {}):
            print(f"{key.upper()}: {value}", file=stream)


def _detect_kind(value: Any) -> str:
    if not isinstance(value, dict):
        raise ValueError("root must be a JSON object")
    if isinstance(value.get("slides"), list):
        return "outline"
    if isinstance(value.get("sources"), list) and "processing" in value:
        return "source-manifest"
    if isinstance(value.get("content"), dict) and "audience" in value:
        return "brief"
    raise ValueError("cannot detect input kind; pass --kind explicitly")


def command_doctor(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    required = [
        "assets/engine.css", "assets/engine.js", "templates/deck.html",
        "references/deck-schema-v2.json",
        "references/agent-response-schema-v1.json",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    ok = sys.version_info >= (3, 10) and not missing
    payload = _result(
        "doctor", ok,
        "engine is ready" if ok else "engine installation is incomplete",
        data={
            "cli_version": CLI_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "deck_schema_version": SCHEMA_VERSION,
            "python": platform.python_version(),
            "root": str(ROOT),
            "response_schema": str(ROOT / "references" / "agent-response-schema-v1.json"),
            "layouts": sorted(LAYOUTS),
            "capabilities": [
                "validate", "build", "production-run", "status", "mark-exported",
                "narrative-director", "visual-coverage-planner", "mcp-stdio", "http-api",
                "production-console",
            ],
        },
        errors=[f"missing {name}" for name in missing]
        + ([] if sys.version_info >= (3, 10) else ["Python 3.10 or newer is required"]),
    )
    return (0 if ok else 2), payload


VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    "outline": validate_outline,
    "brief": validate_brief,
    "source-manifest": validate_manifest,
}


def command_validate(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    try:
        value = _read(args.input.resolve())
        kind = _detect_kind(value) if args.kind == "auto" else args.kind
        errors = VALIDATORS[kind](value)
    except ValueError as exc:
        return 2, _result("validate", False, "input could not be read", errors=[str(exc)])
    ok = not errors
    count = len(value.get("slides", [])) if kind == "outline" else None
    return (
        0 if ok else 1,
        _result(
            "validate", ok,
            f"valid {kind}" if ok else f"invalid {kind}",
            data={"kind": kind, "input": str(args.input.resolve()), "slides": count},
            errors=errors,
        ),
    )


def command_build(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    outline_path = args.outline.resolve()
    output_path = args.out.resolve()
    if outline_path == output_path:
        return 2, _result("build", False, "output must not overwrite the outline")
    try:
        outline = _read(outline_path)
        errors = validate_outline(outline)
        if errors:
            return 1, _result("build", False, "invalid outline", errors=errors)
        assets = args.assets.resolve() if args.assets else ROOT / "assets"
        templates = args.templates.resolve() if args.templates else ROOT / "templates"
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            html, report = build(
                str(outline_path), str(output_path), str(assets), str(templates),
                return_report=True,
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        return 2, _result("build", False, "build failed", errors=[str(exc)])
    warnings = [line for line in stderr.getvalue().splitlines() if line.strip()]
    return 0, _result(
        "build", True, "self-contained deck built",
        data={
            "deck_id": outline["deck_id"],
            "slides": len(outline["slides"]),
            "output": str(output_path),
            "report": report,
        },
        warnings=warnings,
    )


def command_run(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    forwarded = argparse.Namespace(
        outline=args.outline,
        out=args.out,
        brief=args.brief,
        source_manifest=args.source_manifest,
        state=args.state,
        storyboard=None,
        visual_plan=None,
        report=None,
        director_report=None,
        assets=str(args.assets) if args.assets else None,
        templates=str(args.templates) if args.templates else None,
    )
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_pipeline(forwarded)
    state_path = (args.state or args.out.with_name(args.out.stem + ".pipeline-state.json")).resolve()
    state: dict[str, Any] = {}
    if state_path.exists():
        state = _read_json(state_path, "pipeline state")
    errors = state.get("errors", [])
    if code and not errors:
        errors = [line for line in stderr.getvalue().splitlines() if line.strip()]
    return code, _result(
        "run", code == 0,
        "production pipeline is ready" if code == 0 else "production pipeline needs revision",
        data={"state": str(state_path), "pipeline": state},
        errors=errors,
        warnings=state.get("warnings", []),
    )


def command_status(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    try:
        state = _read_json(args.state.resolve(), "pipeline state")
    except ValueError as exc:
        return 2, _result("status", False, "state could not be read", errors=[str(exc)])
    return 0, _result(
        "status", True, f"pipeline is {state.get('status', 'unknown')}",
        data={"state": str(args.state.resolve()), "pipeline": state},
        errors=list(state.get("errors", [])),
        warnings=list(state.get("warnings", [])),
    )


def command_mark_exported(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    forwarded = argparse.Namespace(state=args.state, message=args.message)
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = mark_exported(forwarded)
    try:
        state = _read_json(args.state.resolve(), "pipeline state")
    except ValueError as exc:
        return 2, _result("mark-exported", False, "state could not be read", errors=[str(exc)])
    errors = [] if code == 0 else [line for line in stderr.getvalue().splitlines() if line.strip()]
    return code, _result(
        "mark-exported", code == 0,
        "delivery marked complete" if code == 0 else "delivery state was not changed",
        data={"state": str(args.state.resolve()), "pipeline": state},
        errors=errors,
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Liquid Glass Slides agent CLI")
    root.add_argument("--json", action="store_true", help="emit the stable JSON response envelope")
    commands = root.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="check installation and list capabilities")
    doctor.set_defaults(handler=command_doctor)

    validate = commands.add_parser("validate", help="validate an outline, brief, or source manifest")
    validate.add_argument("input", type=Path)
    validate.add_argument(
        "--kind", choices=("auto", "outline", "brief", "source-manifest"), default="auto"
    )
    validate.set_defaults(handler=command_validate)

    build_parser = commands.add_parser("build", help="validate and build one self-contained HTML deck")
    build_parser.add_argument("--outline", type=Path, required=True)
    build_parser.add_argument("--out", type=Path, required=True)
    build_parser.add_argument("--assets", type=Path)
    build_parser.add_argument("--templates", type=Path)
    build_parser.set_defaults(handler=command_build)

    run = commands.add_parser("run", help="run the recoverable production pipeline")
    run.add_argument("--outline", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--brief", type=Path)
    run.add_argument("--source-manifest", type=Path)
    run.add_argument("--state", type=Path)
    run.add_argument("--assets", type=Path)
    run.add_argument("--templates", type=Path)
    run.set_defaults(handler=command_run)

    status = commands.add_parser("status", help="read a production pipeline state")
    status.add_argument("state", type=Path)
    status.set_defaults(handler=command_status)

    exported = commands.add_parser("mark-exported", help="mark a ready production job as delivered")
    exported.add_argument("state", type=Path)
    exported.add_argument("--message")
    exported.set_defaults(handler=command_mark_exported)
    return root


def main() -> int:
    args = parser().parse_args()
    code, payload = args.handler(args)
    _emit(args, payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
