import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.migrate_outline import migrate_outline
from scripts.validate_outline import validate_outline


ROOT = Path(__file__).resolve().parents[1]


class OutlineProtocolTests(unittest.TestCase):
    def test_machine_readable_schema_declares_v2_identity(self):
        schema = json.loads((ROOT / "references" / "deck-schema-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "2.0")
        self.assertIn("deck_id", schema["required"])
        self.assertIn("slide_id", schema["$defs"]["slide"]["required"])

    def test_v2_examples_validate(self):
        for name in ("sample-outline.json", "narrative-visual-outline.json", "ripple-outline.json"):
            outline = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
            self.assertEqual(validate_outline(outline), [], name)

    def test_duplicate_slide_ids_are_rejected_with_location(self):
        outline = {
            "schema_version": "2.0",
            "deck_id": "demo-deck",
            "title": "Demo",
            "lang": "en",
            "slides": [
                {"slide_id": "same-slide", "layout": "cover", "title": "One"},
                {"slide_id": "same-slide", "layout": "closing", "title": "Two"},
            ],
        }
        self.assertIn("slides[1].slide_id duplicates same-slide", validate_outline(outline))

    def test_migration_ids_survive_reordering(self):
        slides = [
            {"layout": "cover", "title": "稳定身份"},
            {"layout": "comparison", "title": "Address versus content"},
        ]
        first, _ = migrate_outline({"title": "Demo", "slides": slides}, "demo")
        second, _ = migrate_outline({"title": "Demo", "slides": list(reversed(slides))}, "demo")
        first_ids = {slide["title"]: slide["slide_id"] for slide in first["slides"]}
        second_ids = {slide["title"]: slide["slide_id"] for slide in second["slides"]}
        self.assertEqual(first_ids, second_ids)

    def test_migration_cli_updates_legacy_file_in_place(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline_path = Path(temp_dir) / "legacy.json"
            outline_path.write_text(
                json.dumps({"title": "Legacy", "slides": [{"layout": "cover", "title": "Old deck"}]}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "migrate_outline.py"), str(outline_path), "--in-place"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            migrated = json.loads(outline_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_outline(migrated), [])
            self.assertEqual(migrated["schema_version"], "2.0")
            self.assertTrue(migrated["slides"][0]["slide_id"])

    def test_build_stamps_stable_identity_into_dom_and_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "deck.html"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build.py"),
                    "--outline",
                    str(ROOT / "examples" / "narrative-visual-outline.json"),
                    "--out",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            html = output.read_text(encoding="utf-8")
            self.assertIn('data-deck-id="web-crawler-narrative"', html)
            self.assertIn('data-schema-version="2.0"', html)
            self.assertIn('data-slide-id="crawler-loop"', html)
            self.assertIn('"schemaVersion": "2.0"', html)
            self.assertIn('"slideId": "crawler-loop"', html)

    def test_presenter_storage_uses_slide_identity(self):
        js = (ROOT / "assets" / "engine.js").read_text(encoding="utf-8")
        self.assertIn("slides[current].dataset.slideId", js)
        self.assertIn("liquid-glass-notes:v2:", js)
        self.assertIn("legacyDeckNoteKey", js)

    def test_build_rejects_invalid_v2_before_writing_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline_path = Path(temp_dir) / "invalid.json"
            output = Path(temp_dir) / "deck.html"
            outline_path.write_text(
                json.dumps({
                    "schema_version": "2.0",
                    "deck_id": "demo-deck",
                    "title": "Demo",
                    "lang": "en",
                    "slides": [{"layout": "cover", "title": "Missing slide id"}],
                }),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build.py"), "--outline", str(outline_path), "--out", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("slides[0].slide_id", result.stderr)
            self.assertFalse(output.exists())

    def test_legacy_outline_builds_with_migration_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline_path = Path(temp_dir) / "legacy.json"
            output = Path(temp_dir) / "deck.html"
            outline_path.write_text(
                json.dumps({"title": "Legacy", "slides": [{"layout": "cover", "title": "Old deck"}]}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build.py"), "--outline", str(outline_path), "--out", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("legacy outline detected", result.stderr)
            self.assertIn("data-slide-id=", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
