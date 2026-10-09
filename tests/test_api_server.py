import json
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.api_server import create_server


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "narrative-visual-outline.json"
API = ROOT / "scripts" / "api_server.py"
TOKEN = "test-secret-token"


class ApiServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        (self.workspace / "outline.json").write_text(
            EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.server = create_server(self.workspace, "127.0.0.1", 0, TOKEN)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def _request(self, path, method="GET", body=None, token=TOKEN):
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_and_openapi_are_public(self):
        status, health = self._request("/health", token=None)
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        status, spec = self._request("/openapi.json", token=None)
        self.assertEqual(status, 200)
        self.assertEqual(spec["openapi"], "3.1.0")

    def test_private_routes_require_bearer_token(self):
        status, payload = self._request("/v1/capabilities", token=None)
        self.assertEqual(status, 401)
        self.assertFalse(payload["ok"])

    def test_console_is_public_and_session_cookie_unlocks_workspace(self):
        response = urllib.request.urlopen(self.base + "/", timeout=10)
        page = response.read().decode("utf-8")
        self.assertIn("Production Console", page)
        self.assertIn("/console/app.js", page)

        jar = CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        request = urllib.request.Request(
            self.base + "/v1/session",
            data=b"",
            headers={"Authorization": f"Bearer {TOKEN}"},
            method="POST",
        )
        session = opener.open(request, timeout=10)
        self.assertEqual(session.status, 200)
        inventory = json.loads(opener.open(self.base + "/v1/workspace", timeout=10).read())
        self.assertTrue(inventory["ok"])
        self.assertEqual(inventory["data"]["files"][0]["kind"], "outline")

    def test_inventory_and_authenticated_preview(self):
        status, built = self._request(
            "/v1/build", "POST",
            {"outline": "outline.json", "output": "dist/deck.html"},
        )
        self.assertEqual(status, 200)
        status, workspace = self._request("/v1/workspace")
        self.assertEqual(status, 200)
        self.assertEqual(workspace["data"]["decks"][0]["path"], "dist/deck.html")
        request = urllib.request.Request(
            self.base + "/preview?path=dist%2Fdeck.html",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        response = urllib.request.urlopen(request, timeout=10)
        self.assertEqual(response.status, 200)
        self.assertIn(b"<!doctype html>", response.read().lower())

    def test_preview_rejects_non_html_files(self):
        status, payload = self._request("/preview?path=outline.json")
        self.assertEqual(status, 400)
        self.assertIn("HTML", payload["errors"][0])

    def test_validate_and_build(self):
        status, validated = self._request(
            "/v1/validate", "POST", {"path": "outline.json"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(validated["ok"])
        status, built = self._request(
            "/v1/build", "POST",
            {"outline": "outline.json", "output": "dist/deck.html"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(built["ok"])
        self.assertTrue((self.workspace / "dist" / "deck.html").exists())

    def test_workspace_escape_is_rejected(self):
        status, payload = self._request(
            "/v1/build", "POST",
            {"outline": "outline.json", "output": "../escape.html"},
        )
        self.assertEqual(status, 400)
        self.assertIn("inside workspace", payload["errors"][0])

    def test_non_loopback_binding_requires_explicit_opt_in(self):
        result = subprocess.run(
            [sys.executable, str(API), "--workspace", str(self.workspace),
             "--host", "0.0.0.0"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--allow-remote", result.stderr)


if __name__ == "__main__":
    unittest.main()
