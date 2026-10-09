import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "pipeline.py"
EXAMPLE = ROOT / "examples" / "narrative-visual-outline.json"


class ProductionPipelineTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(PIPELINE), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_pipeline_materializes_artifacts_and_ready_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "talk.html"
            result = self._run("run", "--outline", EXAMPLE, "--out", output)
            self.assertEqual(result.returncode, 0, result.stderr)

            state_path = Path(temp_dir) / "talk.pipeline-state.json"
            storyboard_path = Path(temp_dir) / "talk.storyboard.json"
            visual_path = Path(temp_dir) / "talk.visual-plan.json"
            report_path = Path(temp_dir) / "talk.qa-report.json"
            for path in (output, state_path, storyboard_path, visual_path, report_path):
                self.assertTrue(path.exists(), path)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "ready")
            self.assertEqual(state["project_id"], "web-crawler-narrative")
            self.assertEqual(state["stages"]["narrative"]["status"], "complete")
            self.assertEqual(state["stages"]["visual-planning"]["status"], "complete")
            self.assertEqual(state["stages"]["delivery"]["status"], "pending")

            storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
            visual_plan = json.loads(visual_path.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(storyboard["slides"][1]["slide_id"], "crawler-loop")
            self.assertEqual(visual_plan["slides"][1]["layout"], "process-flow")
            self.assertEqual(report["summary"]["slides"], 7)
            self.assertEqual(report["summary"]["runtime_dom_audit"], "pending-browser-open")

            status = self._run("status", state_path)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("STATUS: ready", status.stdout)

            exported = self._run("mark-exported", state_path, "--message", "test delivery")
            self.assertEqual(exported.returncode, 0, exported.stderr)
            final_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(final_state["status"], "exported")
            self.assertEqual(final_state["stages"]["delivery"]["status"], "complete")

    def test_pipeline_state_schema_lists_all_public_statuses(self):
        schema = json.loads(
            (ROOT / "references" / "pipeline-state-schema-v1.json").read_text(encoding="utf-8")
        )
        statuses = schema["properties"]["status"]["enum"]
        self.assertEqual(
            statuses,
            ["draft", "planning", "generating", "validating", "needs_revision", "ready", "exported"],
        )
        self.assertIn("delivery", schema["properties"]["stages"]["required"])

    def test_supplied_brief_requires_source_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            brief = json.loads((ROOT / "examples" / "sample-brief.json").read_text(encoding="utf-8"))
            brief["content"]["mode"] = "supplied"
            brief_path = Path(temp_dir) / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            state_path = Path(temp_dir) / "state.json"
            result = self._run(
                "run", "--brief", brief_path, "--outline", EXAMPLE,
                "--out", Path(temp_dir) / "talk.html", "--state", state_path,
            )
            self.assertEqual(result.returncode, 1)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["sources"]["status"], "failed")
            self.assertIn("source manifest is required", state["errors"][0])

    def test_pipeline_refuses_to_overwrite_an_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline_path = Path(temp_dir) / "outline.json"
            original = EXAMPLE.read_text(encoding="utf-8")
            outline_path.write_text(original, encoding="utf-8")
            result = self._run("run", "--outline", outline_path, "--out", outline_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not overwrite inputs", result.stderr)
            self.assertEqual(outline_path.read_text(encoding="utf-8"), original)

    def test_pipeline_records_actionable_failure_and_recovers_revision(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "invalid.json"
            invalid.write_text(
                json.dumps({
                    "schema_version": "2.0",
                    "deck_id": "bad-deck",
                    "title": "Bad",
                    "lang": "en",
                    "slides": [{"layout": "cover", "title": "Missing identity"}],
                }),
                encoding="utf-8",
            )
            output = Path(temp_dir) / "talk.html"
            state_path = Path(temp_dir) / "state.json"
            failed = self._run(
                "run", "--outline", invalid, "--out", output, "--state", state_path
            )
            self.assertEqual(failed.returncode, 1)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "needs_revision")
            self.assertEqual(state["stages"]["outline"]["status"], "failed")
            self.assertIn("slides[0].slide_id", state["errors"][0])
            self.assertFalse(output.exists())

            recovered = self._run(
                "run", "--outline", EXAMPLE, "--out", output, "--state", state_path
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "ready")
            self.assertEqual(state["revision"], 2)


if __name__ == "__main__":
    unittest.main()
