import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "slides.py"
EXAMPLE = ROOT / "examples" / "narrative-visual-outline.json"


class AgentCliTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), "--json", *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def _payload(self, result):
        return json.loads(result.stdout)

    def test_doctor_reports_stable_capabilities(self):
        result = self._run("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = self._payload(result)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["api_version"], "1.0")
        self.assertIn("production-run", payload["data"]["capabilities"])
        self.assertIn("http-api", payload["data"]["capabilities"])
        self.assertIn("process-flow", payload["data"]["layouts"])
        schema = json.loads(Path(payload["data"]["response_schema"]).read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["api_version"]["const"], "1.0")
        self.assertIn("build", schema["properties"]["command"]["enum"])
        self.assertIn("source-images", schema["properties"]["command"]["enum"])

    def test_validate_auto_detects_outline(self):
        result = self._run("validate", EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = self._payload(result)
        self.assertEqual(payload["data"]["kind"], "outline")
        self.assertEqual(payload["data"]["slides"], 7)

    def test_invalid_outline_uses_structured_error_envelope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text('{"schema_version":"2.0","slides":[]}', encoding="utf-8")
            result = self._run("validate", path, "--kind", "outline")
            self.assertEqual(result.returncode, 1)
            payload = self._payload(result)
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["errors"])

    def test_build_writes_deck_and_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "deck.html"
            result = self._run("build", "--outline", EXAMPLE, "--out", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = self._payload(result)
            self.assertTrue(output.exists())
            self.assertEqual(payload["data"]["slides"], 7)
            self.assertIn("visualCoverage", payload["data"]["report"])

    def test_run_and_status_share_the_same_state_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "deck.html"
            run = self._run("run", "--outline", EXAMPLE, "--out", output)
            self.assertEqual(run.returncode, 0, run.stderr)
            run_payload = self._payload(run)
            state_path = Path(run_payload["data"]["state"])
            self.assertTrue(state_path.exists())
            self.assertEqual(run_payload["data"]["pipeline"]["status"], "ready")

            status = self._run("status", state_path)
            self.assertEqual(status.returncode, 0, status.stderr)
            status_payload = self._payload(status)
            self.assertEqual(status_payload["data"]["pipeline"]["status"], "ready")

            exported = self._run("mark-exported", state_path, "--message", "delivered")
            self.assertEqual(exported.returncode, 0, exported.stderr)
            exported_payload = self._payload(exported)
            self.assertEqual(exported_payload["data"]["pipeline"]["status"], "exported")


if __name__ == "__main__":
    unittest.main()
