import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.source_web_images import source_images


class WebImageSourcingTests(unittest.TestCase):
    def test_sourcing_materializes_unreviewed_manifest(self):
        selected = {
            "id": "abc",
            "title": "Reading group",
            "creator": "Example Photographer",
            "license": "by",
            "license_version": "4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "foreign_landing_url": "https://example.org/image",
            "url": "https://example.org/image.jpg",
            "thumbnail": "https://example.org/thumb.jpg",
            "width": 1600,
            "height": 1000,
            "provider": "example",
            "source": "example",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = root / "media-plan.json"
            manifest = root / "media-manifest.json"
            plan.write_text(json.dumps({
                "deck_id": "test-deck",
                "requests": [{
                    "asset_id": "reading-group",
                    "query": "reading group",
                    "role": "content",
                    "slide_ids": ["discussion"],
                    "alt": "People discussing a book",
                }],
            }), encoding="utf-8")

            def fake_download(_urls, target):
                output = target.with_suffix(".jpg")
                output.write_bytes(b"jpeg")
                return output

            with patch("scripts.source_web_images._get_json", return_value={"results": [selected]}), \
                    patch("scripts.source_web_images._download", side_effect=fake_download):
                result = source_images(plan, root, manifest)

            self.assertFalse(result["reviewed"])
            self.assertEqual(result["assets"][0]["origin"], "web")
            self.assertEqual(result["assets"][0]["local_path"], "images/web/reading-group.jpg")
            self.assertTrue((root / "images/web/reading-group.jpg").exists())


if __name__ == "__main__":
    unittest.main()
