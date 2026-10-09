#!/usr/bin/env python3
"""Run and inspect the recoverable Liquid Glass Slides production pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from build import build
    from validate_brief import validate_brief
    from validate_outline import validate_outline
    from validate_source_manifest import validate_manifest
except ImportError:  # pragma: no cover - module execution fallback
    from scripts.build import build
    from scripts.validate_brief import validate_brief
    from scripts.validate_outline import validate_outline
    from scripts.validate_source_manifest import validate_manifest


PIPELINE_VERSION = "1.0"
STAGE_NAMES = (
    "intake", "sources", "narrative", "visual-planning",
    "outline", "build", "quality", "delivery",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{label} has invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _artifact_path(value: Path | None) -> str | None:
    return str(value.resolve()) if value else None


def _new_state(project_id: str, artifacts: dict[str, str | None], revision: int) -> dict[str, Any]:
    return {
        "pipeline_version": PIPELINE_VERSION,
        "project_id": project_id,
        "revision": revision,
        "status": "draft",
        "updated_at": _now(),
        "artifacts": artifacts,
        "stages": {
            name: {"status": "pending", "message": ""} for name in STAGE_NAMES
        },
        "errors": [],
        "warnings": [],
    }


def _save_state(path: Path, state: dict[str, Any], status: str | None = None) -> None:
    if status:
        state["status"] = status
    state["updated_at"] = _now()
    _atomic_write_json(path, state)


def _stage(state: dict[str, Any], name: str, status: str, message: str) -> None:
    state["stages"][name] = {"status": status, "message": message}


def _speaker_notes(slide: dict[str, Any]) -> str:
    value = slide.get("speaker_notes", slide.get("notes", ""))
    if isinstance(value, list):
        return "\n\n".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def storyboard_from_outline(outline: dict[str, Any]) -> dict[str, Any]:
    slides = []
    for order, slide in enumerate(outline["slides"], 1):
        slides.append({
            "order": order,
            "slide_id": slide["slide_id"],
            "title": slide.get("title", ""),
            "main_point": slide.get("main_point", ""),
            "story_role": slide.get("story_role", ""),
            "audience_question": slide.get("audience_question", ""),
            "speaker_intent": slide.get("speaker_intent", ""),
            "transition": slide.get("transition", ""),
            "emotion": slide.get("emotion", ""),
            "speaker_notes": _speaker_notes(slide),
        })
    return {
        "schema_version": "1.0",
        "deck_id": outline["deck_id"],
        "source_schema_version": outline["schema_version"],
        "slides": slides,
    }


def visual_plan_from_outline(outline: dict[str, Any]) -> dict[str, Any]:
    slides = []
    for order, slide in enumerate(outline["slides"], 1):
        plan = slide.get("visual_plan") if isinstance(slide.get("visual_plan"), dict) else {}
        slides.append({
            "order": order,
            "slide_id": slide["slide_id"],
            "layout": slide["layout"],
            "planned_type": plan.get("type", "auto"),
            "purpose": plan.get("purpose", ""),
            "priority": plan.get("priority", "optional"),
            "source": plan.get("source", ""),
            "has_chart": isinstance(slide.get("chart"), dict),
            "has_image": any(bool(slide.get(key)) for key in ("hero", "src", "image")),
            "has_three": isinstance(slide.get("three"), dict),
            "has_surface": bool(slide.get("surface")),
        })
    return {
        "schema_version": "1.0",
        "deck_id": outline["deck_id"],
        "source_schema_version": outline["schema_version"],
        "slides": slides,
    }


def _report_warnings(report: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for section in ("rhythm", "narrative", "visualCoverage"):
        for warning in report.get(section, {}).get("warnings", []):
            warnings.append({"source": section, **warning})
    for slide in report.get("content", {}).get("slides", []):
        for block in slide.get("longBlocks", []):
            warnings.append({
                "source": "content",
                "code": "long-display-block",
                "slides": [slide.get("slide"), slide.get("slide")],
                "message": "slide %s field %s exceeds %s characters"
                % (slide.get("slide"), block.get("field"), block.get("limit")),
            })
    return warnings


def _existing_revision(state_path: Path) -> int:
    if not state_path.exists():
        return 1
    try:
        previous = json.loads(state_path.read_text(encoding="utf-8"))
        return int(previous.get("revision", 0)) + 1
    except (ValueError, TypeError, json.JSONDecodeError):
        return 1


def run_pipeline(args: argparse.Namespace) -> int:
    outline_path = args.outline.resolve()
    out_path = args.out.resolve()
    stem = out_path.stem
    state_path = (args.state or out_path.with_name(stem + ".pipeline-state.json")).resolve()
    storyboard_path = (args.storyboard or out_path.with_name(stem + ".storyboard.json")).resolve()
    visual_plan_path = (args.visual_plan or out_path.with_name(stem + ".visual-plan.json")).resolve()
    report_path = (args.report or out_path.with_name(stem + ".qa-report.json")).resolve()

    output_paths = [out_path, state_path, storyboard_path, visual_plan_path, report_path]
    input_paths = [outline_path]
    if args.brief:
        input_paths.append(args.brief.resolve())
    if args.source_manifest:
        input_paths.append(args.source_manifest.resolve())
    if len(set(output_paths)) != len(output_paths):
        print("PIPELINE FAILED: output, state, storyboard, visual-plan, and report paths must be distinct", file=sys.stderr)
        return 2
    collisions = set(output_paths).intersection(input_paths)
    if collisions:
        print(
            "PIPELINE FAILED: output paths must not overwrite inputs: "
            + ", ".join(sorted(str(path) for path in collisions)),
            file=sys.stderr,
        )
        return 2

    artifacts = {
        "brief": _artifact_path(args.brief),
        "source_manifest": _artifact_path(args.source_manifest),
        "outline": _artifact_path(outline_path),
        "storyboard": _artifact_path(storyboard_path),
        "visual_plan": _artifact_path(visual_plan_path),
        "deck": _artifact_path(out_path),
        "qa_report": _artifact_path(report_path),
    }
    state = _new_state("unknown-project", artifacts, _existing_revision(state_path))
    _save_state(state_path, state)
    active_stage = "outline"

    try:
        outline = _read_json(outline_path, "outline")
        if isinstance(outline, dict) and isinstance(outline.get("deck_id"), str):
            state["project_id"] = outline["deck_id"]

        _save_state(state_path, state, "planning")
        active_stage = "intake"
        brief = None
        if args.brief:
            brief = _read_json(args.brief.resolve(), "brief")
            brief_errors = validate_brief(brief)
            if brief_errors:
                raise ValueError("invalid brief:\n- " + "\n- ".join(brief_errors))
            if brief.get("confirmed") is not True:
                raise ValueError("brief.confirmed must be true before production")
            _stage(state, "intake", "complete", "brief validated")
        else:
            _stage(state, "intake", "skipped", "no brief supplied")

        active_stage = "sources"
        source_required = bool(
            isinstance(brief, dict)
            and isinstance(brief.get("content"), dict)
            and brief["content"].get("mode") in {"supplied", "assisted"}
        )
        if source_required and not args.source_manifest:
            raise ValueError(
                "source manifest is required when brief.content.mode is supplied or assisted"
            )
        if args.source_manifest:
            source_manifest = _read_json(args.source_manifest.resolve(), "source manifest")
            source_errors = validate_manifest(source_manifest)
            if source_errors:
                raise ValueError("invalid source manifest:\n- " + "\n- ".join(source_errors))
            if source_manifest.get("confirmed") is not True:
                raise ValueError("source_manifest.confirmed must be true before production")
            _stage(state, "sources", "complete", "source manifest validated")
        else:
            _stage(state, "sources", "skipped", "no source manifest supplied")

        active_stage = "outline"
        outline_errors = validate_outline(outline)
        if outline_errors:
            raise ValueError("invalid outline:\n- " + "\n- ".join(outline_errors))
        _stage(state, "outline", "complete", "v2 outline validated")

        active_stage = "narrative"
        _atomic_write_json(storyboard_path, storyboard_from_outline(outline))
        _stage(state, "narrative", "complete", "storyboard snapshot materialized")
        active_stage = "visual-planning"
        _atomic_write_json(visual_plan_path, visual_plan_from_outline(outline))
        _stage(state, "visual-planning", "complete", "visual plan snapshot materialized")
        _save_state(state_path, state, "generating")

        active_stage = "build"
        here = Path(__file__).resolve().parent
        assets = Path(args.assets).resolve() if args.assets else here.parent / "assets"
        templates = Path(args.templates).resolve() if args.templates else here.parent / "templates"
        html, build_report = build(
            str(outline_path), str(out_path), str(assets), str(templates), return_report=True
        )
        _atomic_write_text(out_path, html)
        _stage(state, "build", "complete", "self-contained HTML built")
        _save_state(state_path, state, "validating")

        active_stage = "quality"
        warnings = _report_warnings(build_report)
        quality_report = {
            "pipeline_version": PIPELINE_VERSION,
            "project_id": outline["deck_id"],
            "status": "warnings" if warnings else "pass",
            "summary": {
                "slides": len(outline["slides"]),
                "warnings": len(warnings),
                "runtime_dom_audit": "pending-browser-open",
            },
            "warnings": warnings,
            "build_report": build_report,
        }
        _atomic_write_json(report_path, quality_report)
        state["warnings"] = [warning.get("message", warning.get("code", "warning")) for warning in warnings]
        _stage(
            state,
            "quality",
            "complete",
            "%d build-time warning(s); runtime DOM audit runs when opened" % len(warnings),
        )
        _stage(state, "delivery", "pending", "deck is ready; export or deliver next")
        _save_state(state_path, state, "ready")
    except Exception as exc:
        state["errors"] = [str(exc)]
        _stage(state, active_stage, "failed", str(exc).splitlines()[0])
        for name in STAGE_NAMES:
            if state["stages"][name]["status"] == "pending":
                _stage(state, name, "blocked", "blocked by earlier failure")
        _save_state(state_path, state, "needs_revision")
        print(f"PIPELINE FAILED: {exc}", file=sys.stderr)
        print(f"STATE: {state_path}", file=sys.stderr)
        return 1

    print(f"READY: {out_path}")
    print(f"STATE: {state_path}")
    print(f"QA: {report_path}")
    return 0


def show_status(args: argparse.Namespace) -> int:
    state = _read_json(args.state.resolve(), "pipeline state")
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    print(f"STATUS: {state.get('status', 'unknown')}")
    print(f"PROJECT: {state.get('project_id', 'unknown')}")
    print(f"REVISION: {state.get('revision', 0)}")
    for name in STAGE_NAMES:
        stage = state.get("stages", {}).get(name, {})
        print(f"- {name}: {stage.get('status', 'unknown')} - {stage.get('message', '')}")
    for error in state.get("errors", []):
        print(f"ERROR: {error}")
    return 0


def mark_exported(args: argparse.Namespace) -> int:
    state_path = args.state.resolve()
    state = _read_json(state_path, "pipeline state")
    if state.get("status") not in {"ready", "exported"}:
        print("ERROR: only a ready pipeline can be marked exported", file=sys.stderr)
        return 1
    state["status"] = "exported"
    state["updated_at"] = _now()
    state.setdefault("stages", {})["delivery"] = {
        "status": "complete",
        "message": args.message or "delivery/export confirmed",
    }
    _atomic_write_json(state_path, state)
    print(f"EXPORTED: {state_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Liquid Glass Slides recoverable production pipeline.")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="validate, materialize planning snapshots, build, and report")
    run.add_argument("--outline", type=Path, required=True, help="v2 outline JSON")
    run.add_argument("--out", type=Path, required=True, help="output HTML")
    run.add_argument("--brief", type=Path, help="optional brief.json")
    run.add_argument("--source-manifest", type=Path, help="optional source-manifest.json")
    run.add_argument("--state", type=Path, help="pipeline state JSON path")
    run.add_argument("--storyboard", type=Path, help="storyboard snapshot JSON path")
    run.add_argument("--visual-plan", type=Path, help="visual plan snapshot JSON path")
    run.add_argument("--report", type=Path, help="quality report JSON path")
    run.add_argument("--assets", help="engine assets directory")
    run.add_argument("--templates", help="templates directory")
    run.set_defaults(handler=run_pipeline)

    status = commands.add_parser("status", help="show the latest pipeline state")
    status.add_argument("state", type=Path, help="pipeline state JSON")
    status.add_argument("--json", action="store_true", help="print full machine-readable state")
    status.set_defaults(handler=show_status)

    exported = commands.add_parser("mark-exported", help="mark a ready job as delivered/exported")
    exported.add_argument("state", type=Path, help="pipeline state JSON")
    exported.add_argument("--message", help="optional delivery note")
    exported.set_defaults(handler=mark_exported)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
