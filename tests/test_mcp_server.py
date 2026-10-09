import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "scripts" / "mcp_server.py"
EXAMPLE = ROOT / "examples" / "narrative-visual-outline.json"


def request(method, request_id=None, params=None):
    value = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        value["id"] = request_id
    if params is not None:
        value["params"] = params
    return json.dumps(value, ensure_ascii=False)


class McpServerTests(unittest.TestCase):
    def _session(self, workspace, messages):
        result = subprocess.run(
            [sys.executable, str(SERVER), "--workspace", str(workspace)],
            input="\n".join(messages) + "\n",
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

    def _handshake(self):
        return [
            request("initialize", 1, {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            }),
            request("notifications/initialized"),
        ]

    def _modern_meta(self):
        return {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        }

    def test_modern_discovery_and_stateless_tool_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = self._session(
                temp_dir,
                [
                    request("server/discover", 1, self._modern_meta()),
                    request("tools/list", 2, self._modern_meta()),
                ],
            )
        discover = responses[0]["result"]
        self.assertEqual(discover["supportedVersions"], ["2026-07-28"])
        self.assertEqual(discover["cacheScope"], "public")
        listed = responses[1]["result"]
        self.assertEqual(listed["ttlMs"], 3600000)
        self.assertEqual(
            listed["_meta"]["io.modelcontextprotocol/serverInfo"]["name"],
            "liquid-glass-slides",
        )

    def test_modern_tool_call_needs_no_initialize_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            params = self._modern_meta()
            params.update({"name": "slides_doctor", "arguments": {}})
            responses = self._session(
                temp_dir,
                [request("server/discover", 1, self._modern_meta()),
                 request("tools/call", 2, params)],
            )
        result = responses[1]["result"]
        self.assertEqual(result["resultType"], "complete")
        self.assertTrue(result["structuredContent"]["ok"])
        self.assertEqual(
            result["_meta"]["io.modelcontextprotocol/serverInfo"]["version"], "1.1.0"
        )

    def test_initialize_and_list_tools(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = self._session(
                temp_dir, self._handshake() + [request("tools/list", 2, {})]
            )
        self.assertEqual(responses[0]["result"]["protocolVersion"], "2025-06-18")
        names = [tool["name"] for tool in responses[1]["result"]["tools"]]
        self.assertEqual(
            names,
            ["slides_doctor", "slides_validate", "slides_build", "slides_run",
             "slides_status", "slides_mark_exported"],
        )

    def test_resources_expose_schema_instructions_and_layouts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = self._session(
                temp_dir,
                self._handshake() + [
                    request("resources/list", 2, {}),
                    request("resources/read", 3, {"uri": "slides://schema/deck-v2"}),
                    request("resources/read", 4, {"uri": "slides://layouts"}),
                ],
            )
        uris = [resource["uri"] for resource in responses[1]["result"]["resources"]]
        self.assertIn("slides://instructions", uris)
        schema = json.loads(responses[2]["result"]["contents"][0]["text"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], "2.0")
        layouts = json.loads(responses[3]["result"]["contents"][0]["text"])
        self.assertIn("concept-map", layouts["layouts"])

    def test_doctor_returns_structured_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = self._session(
                temp_dir,
                self._handshake() + [request("tools/call", 2, {
                    "name": "slides_doctor", "arguments": {}
                })],
            )
        result = responses[1]["result"]
        self.assertFalse(result["isError"])
        self.assertTrue(result["structuredContent"]["ok"])
        self.assertEqual(result["structuredContent"]["api_version"], "1.0")

    def test_build_is_limited_to_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            outline = workspace / "outline.json"
            outline.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            responses = self._session(
                workspace,
                self._handshake() + [
                    request("tools/call", 2, {
                        "name": "slides_build",
                        "arguments": {"outline": "outline.json", "output": "dist/deck.html"},
                    }),
                    request("tools/call", 3, {
                        "name": "slides_build",
                        "arguments": {"outline": "outline.json", "output": "../escape.html"},
                    }),
                ],
            )
            self.assertTrue((workspace / "dist" / "deck.html").exists())
        self.assertFalse(responses[1]["result"]["isError"])
        self.assertEqual(responses[2]["error"]["code"], -32602)

    def test_tools_require_initialized_notification(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = self._session(
                temp_dir,
                [request("initialize", 1, {"protocolVersion": "2025-06-18"}),
                 request("tools/list", 2, {})],
            )
        self.assertEqual(responses[1]["error"]["code"], -32002)


if __name__ == "__main__":
    unittest.main()
