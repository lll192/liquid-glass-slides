#!/usr/bin/env python3
"""Diagnose narrative flow and visual coverage without rewriting user facts."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from build import (
        _NON_CLAIM_LAYOUTS,
        _plain_text,
        audit_narrative,
        audit_visual_coverage,
        content_profile,
    )
    from validate_outline import validate_outline
except ImportError:  # pragma: no cover - module execution fallback
    from scripts.build import (
        _NON_CLAIM_LAYOUTS,
        _plain_text,
        audit_narrative,
        audit_visual_coverage,
        content_profile,
    )
    from scripts.validate_outline import validate_outline


DIRECTOR_VERSION = "1.0"
_SEQUENCE_RE = re.compile(r"(^|\s)(step|phase|stage|步骤|阶段|流程|先|再|然后)", re.I)
_COMPARE_RE = re.compile(r"(对比|区别|差异|相比|versus|\bvs\.?\b|before|after)", re.I)


def _note_text(slide: dict[str, Any]) -> str:
    value = slide.get("speaker_notes", slide.get("notes", ""))
    return _plain_text(value)


def _visual_recommendation(slide: dict[str, Any]) -> tuple[str, str]:
    """Choose a semantic visual job, never fabricate the content needed to build it."""
    text = _plain_text(slide)
    items = slide.get("items") if isinstance(slide.get("items"), list) else []
    if _COMPARE_RE.search(text) or slide.get("left_items") or slide.get("right_items"):
        return "comparison", "用并列结构明确两组信息的差异"
    if len(items) >= 3 and (_SEQUENCE_RE.search(text) or any(
            isinstance(item, dict) and str(item.get("label", "")).strip().isdigit()
            for item in items)):
        return "process-flow", "把有先后关系的内容改为可追踪流程"
    if len(items) >= 4:
        return "concept-map", "把多个要点组织成中心概念与关系"
    if re.search(r"\d+(?:\.\d+)?\s*(?:%|％|万|亿|k|m|b)\b", text, re.I):
        return "data-visualization", "页面出现量化信息；仅在数值可追溯时使用图表或表格"
    return "image", "用一张与页面结论直接相关的图片或示意图提供具体对象"


def analyze_outline(outline: dict[str, Any]) -> dict[str, Any]:
    errors = validate_outline(outline)
    if errors:
        raise ValueError("invalid outline:\n- " + "\n- ".join(errors))

    slides = outline["slides"]
    narrative = audit_narrative(slides)
    coverage = audit_visual_coverage(slides)
    pages = []
    substantive = []
    main_points = transitions = notes_ready = explicit_roles = 0

    for index, slide in enumerate(slides):
        page_no = index + 1
        layout = slide.get("layout", "")
        narrative_profile = narrative["slides"][index]
        visual_profile = coverage["slides"][index]
        copy_profile = content_profile(slide)
        structural = layout in _NON_CLAIM_LAYOUTS
        if not structural:
            substantive.append(page_no)

        findings: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []
        if not structural and not narrative_profile["mainPoint"]:
            findings.append({"code": "main-point-missing", "severity": "high"})
            recommendations.append({
                "kind": "copy", "priority": "high",
                "action": "把标题改成页面结论，或补充 main_point",
                "reason": "观众需要知道这一页希望他们记住什么",
            })
        elif not structural:
            main_points += int(bool(narrative_profile["mainPoint"]))

        if narrative_profile["storyRoleSource"] == "inferred":
            recommendations.append({
                "kind": "narrative", "priority": "medium",
                "action": "确认 story_role，当前建议为 %s" % narrative_profile["storyRole"],
                "reason": "明确页面在整段叙事中的职责",
                "suggested_value": narrative_profile["storyRole"],
            })
        else:
            explicit_roles += 1

        if page_no < len(slides) and not narrative_profile["transition"]:
            findings.append({"code": "transition-missing", "severity": "medium"})
            recommendations.append({
                "kind": "delivery", "priority": "medium",
                "action": "补一句通往下一页的自然转场",
                "reason": "避免翻页时突然切断讲述逻辑",
                "next_slide_id": slides[index + 1].get("slide_id"),
            })
        else:
            transitions += int(bool(narrative_profile["transition"]))

        note = _note_text(slide)
        note_length = len(note)
        if not structural and not note:
            findings.append({"code": "speaker-notes-missing", "severity": "high"})
            recommendations.append({
                "kind": "speaker-notes", "priority": "high",
                "action": "写一段约 100 字的自然讲述，解释页面中的具体关系或例子",
                "reason": "演讲者需要可直接开口的内容，而不是规划标签",
            })
        elif not structural and not 70 <= note_length <= 150:
            findings.append({"code": "speaker-notes-length", "severity": "medium", "characters": note_length})
            recommendations.append({
                "kind": "speaker-notes", "priority": "medium",
                "action": "把演讲备注调整到约 80 至 130 个中文字符",
                "reason": "当前长度为 %d，可能过短或过密" % note_length,
            })
        elif not structural:
            notes_ready += 1

        if not structural and not visual_profile["meaningful"]:
            suggested_type, purpose = _visual_recommendation(slide)
            findings.append({"code": "meaningful-visual-missing", "severity": "medium"})
            recommendations.append({
                "kind": "visual", "priority": "medium",
                "action": "评估使用 %s" % suggested_type,
                "reason": purpose,
                "suggested_value": suggested_type,
                "requires_source_check": suggested_type == "data-visualization",
            })

        if copy_profile["longBlocks"]:
            findings.append({"code": "display-copy-dense", "severity": "high", "blocks": copy_profile["longBlocks"]})
            recommendations.append({
                "kind": "copy", "priority": "high",
                "action": "缩短屏幕文案，把解释移入 speaker_notes，必要时拆页",
                "reason": "页面存在超过安全长度的文字块",
            })

        pages.append({
            "slide": page_no,
            "slide_id": slide["slide_id"],
            "layout": layout,
            "title": _plain_text(slide.get("title")),
            "story_role": narrative_profile["storyRole"],
            "emotion": narrative_profile["emotion"],
            "main_point": narrative_profile["mainPoint"],
            "actual_visual": visual_profile["actualType"],
            "findings": findings,
            "recommendations": recommendations,
        })

    substantive_count = len(substantive)
    transition_slots = max(1, len(slides) - 1)
    metrics = {
        "substantive_slides": substantive_count,
        "main_point_coverage": round(main_points / max(1, substantive_count), 3),
        "explicit_role_coverage": round(explicit_roles / max(1, len(slides)), 3),
        "transition_coverage": round(transitions / transition_slots, 3),
        "speaker_notes_ready": round(notes_ready / max(1, substantive_count), 3),
        "meaningful_visual_coverage": coverage["coverage"],
        "role_diversity": len({page["story_role"] for page in pages}),
    }
    score = round(100 * (
        .20 * metrics["main_point_coverage"]
        + .15 * metrics["explicit_role_coverage"]
        + .15 * metrics["transition_coverage"]
        + .20 * metrics["speaker_notes_ready"]
        + .30 * min(1.0, metrics["meaningful_visual_coverage"] / .5)
    ))
    high = sum(
        finding["severity"] == "high"
        for page in pages for finding in page["findings"]
    )
    return {
        "director_version": DIRECTOR_VERSION,
        "deck_id": outline["deck_id"],
        "status": "needs_revision" if high else ("review" if any(page["findings"] for page in pages) else "ready"),
        "score": score,
        "metrics": metrics,
        "deck_findings": narrative["warnings"] + coverage["warnings"],
        "pages": pages,
        "guardrails": [
            "不自动改写用户事实、数字或受保护原文",
            "图表建议必须先确认存在可追溯的量化数据",
            "自动补全仅限可由现有结构确定的元数据",
        ],
    }


def apply_safe_metadata(outline: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    enriched = copy.deepcopy(outline)
    by_id = {page["slide_id"]: page for page in report["pages"]}
    for slide in enriched["slides"]:
        page = by_id[slide["slide_id"]]
        slide.setdefault("story_role", page["story_role"])
        slide.setdefault("emotion", page["emotion"])
        if not _plain_text(slide.get("main_point")) and content_profile(slide)["titleQuality"] == "claim":
            slide["main_point"] = _plain_text(slide.get("title"))
        if "visual_plan" not in slide and page["actual_visual"] not in {"text", "decorative"}:
            slide["visual_plan"] = {
                "type": page["actual_visual"],
                "purpose": "记录现有页面的主要信息视觉",
                "priority": "optional",
            }
    return enriched


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose narrative and visual coverage for a v2 outline.")
    parser.add_argument("outline", type=Path)
    parser.add_argument("--report", type=Path, help="write machine-readable director report")
    parser.add_argument("--apply-safe", type=Path, metavar="OUTLINE", help="write a copy with safe inferred metadata")
    args = parser.parse_args()
    try:
        outline = json.loads(args.outline.read_text(encoding="utf-8"))
        report = analyze_outline(outline)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    if args.report:
        _write_json(args.report, report)
    if args.apply_safe:
        _write_json(args.apply_safe, apply_safe_metadata(outline, report))
    print("DIRECTOR: %s (%d/100)" % (report["status"], report["score"]))
    print("PAGES WITH FINDINGS: %d" % sum(bool(page["findings"]) for page in report["pages"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
