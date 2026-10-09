import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "content_director.py"
EXAMPLE = ROOT / "examples" / "narrative-visual-outline.json"


class ContentDirectorTests(unittest.TestCase):
    def test_reference_outline_receives_machine_readable_diagnosis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "director.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(EXAMPLE), "--report", str(report_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["deck_id"], "web-crawler-narrative")
            self.assertEqual(len(report["pages"]), 7)
            self.assertGreaterEqual(report["score"], 80)
            self.assertEqual(report["pages"][1]["actual_visual"], "process-flow")
            self.assertEqual(report["pages"][1]["findings"], [])

    def test_missing_content_fields_produce_specific_actions(self):
        outline = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        slide = outline["slides"][1]
        slide["layout"] = "bullets"
        slide["title"] = "基本概念"
        for key in ("main_point", "story_role", "emotion", "transition", "speaker_notes", "visual_plan"):
            slide.pop(key, None)
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "outline.json"
            report_path = Path(temp_dir) / "report.json"
            source.write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--report", str(report_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            page = json.loads(report_path.read_text(encoding="utf-8"))["pages"][1]
            codes = {item["code"] for item in page["findings"]}
            self.assertIn("main-point-missing", codes)
            self.assertIn("speaker-notes-missing", codes)
            self.assertIn("transition-missing", codes)
            self.assertIn("meaningful-visual-missing", codes)

    def test_apply_safe_only_adds_structural_metadata(self):
        outline = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        slide = outline["slides"][1]
        original_items = slide["items"]
        for key in ("story_role", "emotion", "main_point", "visual_plan"):
            slide.pop(key, None)
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "outline.json"
            enriched = Path(temp_dir) / "enriched.json"
            source.write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--apply-safe", str(enriched)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(enriched.read_text(encoding="utf-8"))["slides"][1]
            self.assertEqual(updated["story_role"], "explain")
            self.assertEqual(updated["emotion"], "clarity")
            self.assertEqual(updated["main_point"], updated["title"])
            self.assertEqual(updated["visual_plan"]["type"], "process-flow")
            self.assertEqual(updated["items"], original_items)
            self.assertEqual(updated["speaker_notes"], slide["speaker_notes"])


if __name__ == "__main__":
    unittest.main()
