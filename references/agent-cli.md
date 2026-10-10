# Agent CLI contract

`scripts/slides.py` is the stable command boundary for AI platforms, local automation,
future API wrappers, and MCP servers. Integrations should call this facade instead of
coupling themselves to individual implementation scripts.

## Response envelope

Pass `--json` before the command to receive one JSON object on standard output:

```json
{
  "api_version": "1.0",
  "command": "build",
  "ok": true,
  "message": "self-contained deck built",
  "data": {},
  "errors": [],
  "warnings": []
}
```

Fields are always present. Human-readable diagnostics from the underlying engine are
normalized into `errors` or `warnings`, so agents do not need to scrape terminal prose.
The machine-readable contract lives in `references/agent-response-schema-v1.json`.

Exit codes:

- `0`: command completed successfully.
- `1`: input was readable but needs revision, such as a schema validation failure.
- `2`: invocation, file access, JSON parsing, installation, or output-path failure.

## Commands

Check the installation and discover capabilities:

```bash
python scripts/slides.py --json doctor
```

Validate any supported input. `auto` distinguishes outlines, briefs, source manifests,
and media manifests:

```bash
python scripts/slides.py --json validate outline.json
python scripts/slides.py --json validate brief.json --kind brief
python scripts/slides.py --json validate media-manifest.json --kind media-manifest
```

Validate and build a single self-contained deck:

```bash
python scripts/slides.py --json build --outline outline.json --out dist/deck.html
```

Search Openverse in parallel, download reusable real-world images, and create an
unreviewed provenance manifest:

```bash
python scripts/slides.py --json source-images --plan media-plan.json --project-dir . --manifest media-manifest.json
```

Review every candidate before setting `reviewed:true`; search relevance alone does not
approve an image.

Run the recoverable production pipeline:

```bash
python scripts/slides.py --json run --outline outline.json --media-manifest media-manifest.json --out dist/deck.html
```

Read a job state without parsing human-readable output:

```bash
python scripts/slides.py --json status dist/deck.pipeline-state.json
```

Record successful delivery:

```bash
python scripts/slides.py --json mark-exported dist/deck.pipeline-state.json --message "delivered"
```

## Integration rules

1. Run `doctor` once after installation or update.
2. Use `validate` before requesting expensive assets or external services.
3. Use `build` for a deterministic one-file render and `run` for production work that
   needs storyboard, visual plan, QA report, and resumable state.
4. Treat `data` as command-specific payload. Treat the top-level envelope as stable.
5. Display `errors` to the agent or user without guessing a repair that changes factual
   content. Warnings may be resolved iteratively.
6. Do not parse text mode in an integration. Text mode exists only for humans.

The previous scripts remain supported as internal and advanced entry points. The facade
does not duplicate their business logic.
