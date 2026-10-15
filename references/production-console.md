# Engine Cockpit

The Engine Cockpit is the local, buildless human interface over the same production core used by the Agent CLI, MCP server, and HTTP API. It turns internal engine decisions into a reviewable product without a domain, cloud account, or hosted server.

## Start

Run from the repository root and point `--workspace` at one presentation project:

```bash
python scripts/api_server.py --workspace C:/path/to/presentation-project --open
```

`--open` launches the default browser with the bearer token in the URL fragment. Fragments are not sent in HTTP requests; the page exchanges it for an HttpOnly same-site session and removes it from the address bar. Without `--open`, paste the terminal token into the connection screen.

## Five project views

1. **成品预览** — inspect the newest generated deck and open it for rehearsal.
2. **故事线** — read every slide's story role, claim, and transition from Narrative Director; directly edit the title, main point, transition, and speaker notes.
3. **视觉覆盖** — see meaningful-visual coverage and each slide's actual visual type from Visual Coverage Planner.
4. **媒体库** — preview local images, distinguish web and AI origins, read attribution, reject candidates, and approve the final selection.
5. **连接 AI** — copy a ready-to-use AI task or MCP configuration, test the local engine, and install the Codex Skill with one click.

## Production workflow

1. Select a detected v2 outline.
2. Review narrative, visual coverage, and existing media before generation.
3. Optionally select a `media-plan.json` and run **搜索真实图片**.
4. Reject weak candidates in the media library, then approve the retained set.
5. Select the reviewed media manifest for the production run.
6. Use **验证结构** for a fast schema check, **快速构建** for HTML only, or **完整生产** for storyboard, visual plan, director report, QA report, state, and HTML.
7. Read errors and warnings in the report rail, then inspect or rehearse the deck.

The file inventory ignores `.git`, `.venv`, `node_modules`, hidden directories, and Python caches. Every input, image, report, and preview stays inside the configured workspace boundary.

## Security model

- The server listens on loopback only unless `--allow-remote` is explicitly supplied.
- API calls require a bearer token or the local HttpOnly session cookie.
- Only image assets and existing HTML files inside the workspace can be previewed.
- The Cockpit has no CDN, analytics, external fonts, or third-party runtime.
- Remote exposure must sit behind TLS, authentication, and a trusted firewall.

## AI collaboration

The AI remains responsible for ambiguous planning, research, writing, and revision. The Cockpit handles choices that are easier to make visually: story review, coverage gaps, candidate selection, build status, and final acceptance. Both operate on the same stable `deck_id`, `slide_id`, manifests, and reports, so work can move between conversation and visual review without creating a second project format.
