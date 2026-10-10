import tempfile
import unittest
from pathlib import Path

from scripts.install_plugin import install


class InstallPluginTests(unittest.TestCase):
    def test_install_creates_complete_local_skill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "liquid-glass-slides"
            copied = install(destination, update=False, dry_run=False)
            self.assertIn("SKILL.md", copied)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertTrue((destination / "agents" / "openai.yaml").is_file())
            self.assertTrue((destination / "scripts" / "mcp_server.py").is_file())
            self.assertTrue((destination / "console" / "index.html").is_file())

    def test_existing_destination_requires_update(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "liquid-glass-slides"
            destination.mkdir()
            with self.assertRaises(ValueError):
                install(destination, update=False, dry_run=False)


if __name__ == "__main__":
    unittest.main()
