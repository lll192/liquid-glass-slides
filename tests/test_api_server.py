import base64
import json
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from scripts.api_server import create_server
from scripts.agent_service import AgentService
from scripts.source_web_images import SourceError


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
        self.assertIn("Engine Cockpit", page)
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

    def test_project_inspection_media_preview_and_review(self):
        image_dir = self.workspace / "images"
        image_dir.mkdir()
        (image_dir / "candidate.jpg").write_bytes(b"candidate-image")
        manifest = {
            "schema_version": "1.0", "deck_id": "web-crawler-narrative",
            "reviewed": False,
            "assets": [{
                "asset_id": "candidate-photo", "origin": "web", "role": "content",
                "local_path": "images/candidate.jpg", "slide_ids": ["crawler-opening-question"],
                "alt": "候选图片", "fit": "cover", "focal_point": "50% 50%",
                "source_url": "https://example.com/source", "license_url": "https://example.com/license",
                "license": "CC BY 4.0", "author": "Example",
            }],
        }
        (self.workspace / "media-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        status, inspected = self._request("/v1/project?outline=outline.json")
        self.assertEqual(status, 200)
        self.assertEqual(inspected["data"]["deck"]["deck_id"], "web-crawler-narrative")
        self.assertEqual(inspected["data"]["metrics"]["web_assets"], 1)
        self.assertIn("content_fields", inspected["data"]["slides"][0])
        asset_path = inspected["data"]["media"]["assets"][0]["asset_path"]
        request = urllib.request.Request(
            self.base + "/asset?path=" + urllib.parse.quote(asset_path),
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(urllib.request.urlopen(request, timeout=10).read(), b"candidate-image")
        status, reviewed = self._request(
            "/v1/review-media", "POST",
            {"manifest": "media-manifest.json", "outline": "outline.json",
             "selectedAssetIds": ["candidate-photo"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(reviewed["data"]["reviewed"])
        self.assertEqual(reviewed["data"]["applied_slides"], ["crawler-opening-question"])
        applied_outline = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        self.assertEqual(applied_outline["slides"][0]["hero"], "images/candidate.jpg")
        status, built = self._request(
            "/v1/build", "POST",
            {"outline": "outline.json", "output": "dist/media-applied.html"},
        )
        self.assertEqual(status, 200)
        built_html = (self.workspace / "dist" / "media-applied.html").read_text(encoding="utf-8")
        self.assertIn("data:image/jpeg;base64,Y2FuZGlkYXRlLWltYWdl", built_html)
        first_slide_id = json.loads(EXAMPLE.read_text(encoding="utf-8"))["slides"][0]["slide_id"]
        status, updated = self._request(
            "/v1/update-slide", "POST",
            {
                "outline": "outline.json", "slideId": first_slide_id,
                "patch": {"main_point": "控制台已完成精确修改"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["data"]["slide_id"], first_slide_id)
        saved = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["slides"][0]["main_point"], "控制台已完成精确修改")

    def test_project_recovers_used_image_and_keeps_unselected_library_assets(self):
        image_dir = self.workspace / "images"
        image_dir.mkdir()
        (image_dir / "used.jpg").write_bytes(b"used-image")
        (image_dir / "used-gallery.jpg").write_bytes(b"used-gallery-image")
        (image_dir / "candidate.jpg").write_bytes(b"candidate-image")
        outline = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        target = outline["slides"][0]
        target["background_image"] = "images/used.jpg"
        target["background_alt"] = "正在演示中使用的图片"
        target["background_opacity"] = 1
        target["support_images"] = [{
            "src": "images/used-gallery.jpg", "alt": "正在页面中显示的内容图",
            "fit": "cover", "position": "50% 50%",
        }]
        (self.workspace / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False), encoding="utf-8"
        )
        manifest = {
            "schema_version": "1.0", "deck_id": "web-crawler-narrative",
            "reviewed": True,
            "assets": [{
                "asset_id": "candidate-photo", "origin": "project-asset", "role": "content",
                "local_path": "images/candidate.jpg", "slide_ids": ["crawler-opening-question"],
                "alt": "候选图片", "fit": "cover", "focal_point": "50% 50%",
            }],
        }
        (self.workspace / "media-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )

        status, inspected = self._request(
            "/v1/project?outline=outline.json&mediaManifest=media-manifest.json"
        )
        self.assertEqual(status, 200)
        recovered = next(
            asset for asset in inspected["data"]["media"]["assets"]
            if asset["local_path"] == "images/used.jpg"
        )
        self.assertEqual(recovered["origin"], "project-asset")
        recovered_gallery = next(
            asset for asset in inspected["data"]["media"]["assets"]
            if asset["local_path"] == "images/used-gallery.jpg"
        )
        self.assertEqual(recovered_gallery["role"], "content")
        self.assertTrue(recovered_gallery["in_use"])
        self.assertEqual(recovered["opacity"], 1)

        status, reviewed = self._request(
            "/v1/review-media", "POST",
            {"manifest": "media-manifest.json", "outline": "outline.json",
             "selectedAssetIds": [recovered["asset_id"], recovered_gallery["asset_id"]]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["data"]["assets"], 2)
        self.assertEqual(reviewed["data"]["library_assets"], 3)
        saved_manifest = json.loads(
            (self.workspace / "media-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(saved_manifest["assets"]), 3)
        candidate = next(
            asset for asset in saved_manifest["assets"]
            if asset["asset_id"] == "candidate-photo"
        )
        self.assertFalse(candidate["selected"])
        saved_outline = json.loads(
            (self.workspace / "outline.json").read_text(encoding="utf-8")
        )
        saved_target = saved_outline["slides"][0]
        self.assertEqual(saved_target["background_image"], "images/used.jpg")
        self.assertEqual(saved_target["hero"], "images/used-gallery.jpg")

    def test_add_media_translates_chinese_search_and_keeps_connection(self):
        manifest = {
            "schema_version": "1.0", "deck_id": "web-crawler-narrative",
            "reviewed": True, "assets": [],
        }
        (self.workspace / "media-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        captured = {"queries": []}

        def fake_source(plan_path, project_dir, manifest_path, reviewed=False, workers=1):
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            candidate = plan["requests"][0]["query"]
            captured["queries"].append(candidate)
            if "elegant" in candidate:
                raise SourceError("exact query returned no results")
            return {"assets": [{
                "asset_id": plan["requests"][0]["asset_id"], "origin": "web",
                "role": "content", "local_path": "images/web/result.jpg",
                "slide_ids": ["opening"], "alt": "优雅老人", "fit": "cover",
                "focal_point": "50% 50%", "source_url": "https://example.com",
                "license_url": "https://example.com/license", "license": "CC0",
                "author": "Example",
            }]}

        with mock.patch("scripts.agent_service.source_images", side_effect=fake_source):
            status, payload = self._request(
                "/v1/add-media", "POST",
                {"manifest": "media-manifest.json", "query": "白人老男人优雅",
                 "slideId": "opening", "role": "content"},
            )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("elegant", captured["queries"][0])
        self.assertEqual(captured["queries"][1], "elderly man portrait")
        self.assertEqual(payload["data"]["search_query"], "elderly man portrait")

    def test_non_person_image_search_does_not_force_portrait(self):
        self.assertEqual(
            AgentService._image_search_query("一杯摆在桌子上的咖啡"),
            "coffee cup on table",
        )
        self.assertEqual(
            AgentService._image_search_query("一杯摆在桌子上的星巴克咖啡"),
            "cup on table Starbucks coffee",
        )
        self.assertEqual(AgentService._image_search_queries("完全无法识别的词语"), [])
        self.assertEqual(AgentService._image_search_query("北欧冬日街道"), "Nordic winter street")
        self.assertEqual(AgentService._image_search_query("薯片"), "potato chips")
        self.assertEqual(
            AgentService._image_search_query("身穿比基尼的亚洲美女"),
            "wearing bikini Asian woman portrait photograph",
        )

    def test_local_upload_supports_multiple_content_and_one_background(self):
        manifest_path = self.workspace / "media-manifest.json"
        manifest_path.write_text(json.dumps({
            "schema_version": "1.0", "deck_id": "web-crawler-narrative",
            "reviewed": True, "assets": [],
        }), encoding="utf-8")
        encoded = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 32).decode("ascii")
        ids = []
        for name, role in (("one.png", "content"), ("two.png", "content"), ("bg.png", "background")):
            status, payload = self._request("/v1/upload-media", "POST", {
                "manifest": "media-manifest.json", "filename": name, "data": encoded,
                "slideId": "crawler-loop", "role": role, "opacity": 0.42,
            })
            self.assertEqual(status, 200)
            ids.append(payload["data"]["asset_id"])
        status, payload = self._request("/v1/review-media", "POST", {
            "manifest": "media-manifest.json", "outline": "outline.json",
            "selectedAssetIds": ids,
        })
        self.assertEqual(status, 200)
        outline = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        opening = next(slide for slide in outline["slides"] if slide["slide_id"] == "crawler-loop")
        self.assertEqual(len(opening["support_images"]), 2)
        self.assertEqual(opening["support_gallery_mode"], "right-grid")
        self.assertEqual(opening["background_opacity"], 0.42)
        status, payload = self._request("/v1/update-media", "POST", {
            "manifest": "media-manifest.json", "outline": "outline.json",
            "assetId": ids[-1], "opacity": 0.27,
        })
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["applied_slides"], ["crawler-loop"])
        updated = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        opening = next(slide for slide in updated["slides"] if slide["slide_id"] == "crawler-loop")
        self.assertEqual(opening["background_opacity"], 0.27)
        for extreme in (0, 1):
            status, payload = self._request("/v1/update-media", "POST", {
                "manifest": "media-manifest.json", "outline": "outline.json",
                "assetId": ids[-1], "opacity": extreme,
            })
            self.assertEqual(status, 200)
            self.assertEqual(payload["data"]["opacity"], extreme)
            updated = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
            opening = next(slide for slide in updated["slides"] if slide["slide_id"] == "crawler-loop")
            self.assertEqual(opening["background_opacity"], extreme)

    def test_one_file_cannot_render_as_background_and_content_on_same_slide(self):
        image_dir = self.workspace / "images"
        image_dir.mkdir()
        (image_dir / "same.jpg").write_bytes(b"same")
        outline = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        target = outline["slides"][1]
        target["image"] = "images/same.jpg"
        target["background_image"] = "images/same.jpg"
        target["background_opacity"] = 0.8
        (self.workspace / "outline.json").write_text(json.dumps(outline), encoding="utf-8")
        manifest = {
            "schema_version": "1.0", "deck_id": "web-crawler-narrative", "reviewed": False,
            "assets": [{
                "asset_id": "same-photo", "origin": "user-provided", "role": "content",
                "local_path": "images/same.jpg", "slide_ids": [target["slide_id"]],
                "alt": "same photo", "selected": True,
            }],
        }
        (self.workspace / "media-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        status, _payload = self._request("/v1/review-media", "POST", {
            "manifest": "media-manifest.json", "outline": "outline.json",
            "selectedAssetIds": ["same-photo"],
        })
        self.assertEqual(status, 200)
        applied = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))["slides"][1]
        self.assertNotIn("background_image", applied)
        self.assertNotIn("background_opacity", applied)
        self.assertNotIn("image", applied)
        self.assertEqual(applied["support_images"][0]["src"], "images/same.jpg")

    def test_removed_decorations_stay_removed_across_duplicate_manifests(self):
        image_dir = self.workspace / "images"
        image_dir.mkdir()
        for name in ("decor-one.jpg", "decor-two.jpg"):
            (image_dir / name).write_bytes(name.encode("ascii"))
        outline = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        target = outline["slides"][1]
        target["decorative_images"] = [
            {"src": "images/decor-one.jpg", "alt": "装饰一", "fit": "cover", "position": "50% 50%"},
            {"src": "images/decor-two.jpg", "alt": "装饰二", "fit": "cover", "position": "50% 50%"},
        ]
        (self.workspace / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False), encoding="utf-8"
        )
        assets = [{
            "asset_id": f"decor-{index}", "origin": "user-provided", "role": "decorative",
            "local_path": f"images/decor-{name}.jpg", "slide_ids": [target["slide_id"]],
            "alt": f"装饰{index}", "selected": True,
        } for index, name in enumerate(("one", "two"), 1)]
        for manifest_name in ("media-manifest.json", "media-manifest-web.json"):
            (self.workspace / manifest_name).write_text(json.dumps({
                "schema_version": "1.0", "deck_id": "web-crawler-narrative",
                "reviewed": False, "assets": assets,
            }, ensure_ascii=False), encoding="utf-8")

        status, payload = self._request("/v1/review-media", "POST", {
            "manifest": "media-manifest-web.json", "outline": "outline.json",
            "selectedAssetIds": [],
        })
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["assets"], 0)
        self.assertEqual(payload["data"]["synchronized_manifests"], ["media-manifest.json"])
        saved_outline = json.loads((self.workspace / "outline.json").read_text(encoding="utf-8"))
        self.assertNotIn("decorative_images", saved_outline["slides"][1])
        sibling = json.loads((self.workspace / "media-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(all(asset["selected"] is False for asset in sibling["assets"]))

        status, inspected = self._request(
            "/v1/project?outline=outline.json&mediaManifest=media-manifest.json"
        )
        self.assertEqual(status, 200)
        self.assertTrue(all(asset["selected"] is False for asset in inspected["data"]["media"]["assets"]))
        status, built = self._request("/v1/build", "POST", {
            "outline": "outline.json", "output": "dist/no-decor.html",
        })
        self.assertEqual(status, 200)
        html = (self.workspace / "dist" / "no-decor.html").read_text(encoding="utf-8")
        self.assertNotIn('<div class="slide-decor-gallery"', html)

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
