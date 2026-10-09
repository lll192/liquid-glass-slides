# Production Console

The production console is a local, buildless interface over the same presentation core used by the Agent CLI, MCP server, and HTTP API. It is designed for human review before GitHub delivery or public promotion.

## Start

Run from the repository root and point `--workspace` at the folder that contains the presentation outline and its optional brief or source manifest:

```bash
python scripts/api_server.py --workspace C:/path/to/presentation-project
```

Open `http://127.0.0.1:8765`. Paste the generated Bearer Token from the terminal into the connection screen. The console exchanges it for an HttpOnly, same-site browser session; it does not save the token in the project or browser local storage.

## Workflow

1. Choose a detected v2 outline from the workspace.
2. Keep or edit the suggested `dist/<deck>.html` output path.
3. Optionally select a validated design brief and source manifest.
4. Use **Validate outline** for a fast structural check.
5. Use **Quick build** when the outline is ready and only the HTML is needed.
6. Use **Full production** for storyboard, visual plan, director report, QA report, state file, and HTML.
7. Read errors and warnings in the report rail, then inspect the deck in the embedded preview or a new tab.

The file inventory is bounded and ignores `.git`, `.venv`, `node_modules`, hidden directories, and Python cache folders. Every selected path and preview remains inside the workspace boundary.

## Security model

- The server listens on loopback only unless `--allow-remote` is explicitly supplied.
- API calls require a Bearer Token or the local HttpOnly session cookie.
- Only existing `.html` files inside the workspace can be previewed.
- The console is static and has no CDN, analytics, external fonts, or third-party runtime.
- Remote exposure should be placed behind TLS, authentication, and a trusted firewall. The local cookie is intentionally not marked `Secure` because the default server uses loopback HTTP.

## Intended handoff

The console is the human-facing acceptance gate. AI clients may create or revise `outline.json` through CLI, MCP, or API; the human can then validate, build, inspect warnings, rehearse the generated deck, and decide when to commit or publish.
