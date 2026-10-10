import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_media_manifest import validate_media_manifest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "slides.py"
EXAMPLE = ROOT / "examples" / "narrative-visual-outline.json"


def sample_manifest():
    return {
        "schema_version": "1.0",
        "deck_id": "web-crawler-narrative",
        "reviewed": True,
        "assets": [{
            "asset_id": "crawler-photo",
            "origin": "web",
            "role": "content",
            "local_path": "images/crawler.jpg",
            "slide_ids": ["crawler-loop"],
            "alt": "A crawler illustration",
            "fit": "cover",
            "focal_point": "60% 50%",
            "source_url": "https://example.org/photo",
            "author": "Example Author",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
        }],
    }


class MediaManifestTests(unittest.TestCase):
    def test_web_asset_requires_license_provenance(self):
        manifest = sample_manifest()
        self.assertEqual(validate_media_manifest(manifest), [])
        del manifest["assets"][0]["license"]
        self.assertIn("assets[0].license is required for web assets", validate_media_manifest(manifest))

    def test_local_paths_cannot_escape_project(self):
        manifest = sample_manifest()
        manifest["assets"][0]["local_path"] = "../outside.jpg"
        self.assertIn(
            "assets[0].local_path must be a safe relative path",
            validate_media_manifest(manifest),
        )

    def test_agent_cli_validates_and_pipeline_accepts_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "media-manifest.json"
            manifest_path.write_text(json.dumps(sample_manifest()), encoding="utf-8")
            validate = subprocess.run(
                [sys.executable, str(CLI), "--json", "validate", str(manifest_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(validate.returncode, 0, validate.stderr)
            self.assertEqual(json.loads(validate.stdout)["data"]["kind"], "media-manifest")
            output = Path(temp_dir) / "deck.html"
            run = subprocess.run(
                [sys.executable, str(CLI), "--json", "run", "--outline", str(EXAMPLE),
                 "--media-manifest", str(manifest_path), "--out", str(output)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            state = json.loads(
                (Path(temp_dir) / "deck.pipeline-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(Path(state["artifacts"]["media_manifest"]), manifest_path)


if __name__ == "__main__":
    unittest.main()
