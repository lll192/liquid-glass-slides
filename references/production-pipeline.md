# Recoverable Production Pipeline

Use this workflow when an AI agent needs a repeatable, inspectable build rather than a
single opaque generation step. The pipeline does not invent slide content. It validates
the authored inputs, materializes planning snapshots, builds the deck, and records what
happened so another agent or a later run can continue from the failure point.

## One-command run

```bash
python scripts/pipeline.py run \
  --brief brief.json \
  --source-manifest source-manifest.json \
  --outline outline.json \
  --out dist/talk.html
```

`--brief` and `--source-manifest` are optional for an outline-only build. When supplied,
they are validated before generation. Output paths default beside the HTML file:

- `talk.storyboard.json` — narrative snapshot keyed by stable `slide_id`.
- `talk.visual-plan.json` — layout and visual-coverage snapshot.
- `talk.director-report.json` — editorial readiness score and per-slide revision actions.
- `talk.qa-report.json` — build-time rhythm, content, narrative, and coverage report.
- `talk.pipeline-state.json` — current job status, artifact paths, errors, and warnings.

All files are written atomically so an interrupted run does not replace the last valid
artifact with a partial file.

## Status model

The top-level job status is one of:

| Status | Meaning |
|---|---|
| `draft` | State exists but planning has not started. |
| `planning` | Brief, sources, and outline are being checked. |
| `generating` | Planning snapshots are complete and HTML is being built. |
| `validating` | HTML exists and the quality report is being assembled. |
| `needs_revision` | A precise input/build error requires correction. |
| `ready` | HTML and build-time QA artifacts are complete. |
| `exported` | A human or external exporter confirmed delivery. |

Inspect a job without rebuilding it:

```bash
python scripts/pipeline.py status dist/talk.pipeline-state.json
python scripts/pipeline.py status dist/talk.pipeline-state.json --json
```

After delivery or a future PDF/PPTX export:

```bash
python scripts/pipeline.py mark-exported dist/talk.pipeline-state.json \
  --message "HTML delivered to reviewer"
```

## Stage model

Every state records `intake`, `sources`, `narrative`, `visual-planning`, `outline`,
`build`, `quality`, and `delivery`. A stage is `pending`, `complete`, `skipped`,
`failed`, or `blocked`. Optional missing inputs are marked `skipped`, not silently
treated as complete.

The pipeline keeps factual and creative responsibility with the producing agent:

1. The agent collects and validates the brief.
2. The agent resolves supplied-source requirements.
3. The agent authors the v2 outline with stable identities.
4. The pipeline extracts inspectable narrative and visual snapshots.
5. Content Director diagnoses narrative, notes, copy, and visual gaps without rewriting facts.
6. The deterministic builder emits HTML and build-time QA.
7. The browser performs the runtime DOM audit when the deck is opened.

`ready` therefore means deterministic generation and build-time QA completed. The
quality report explicitly leaves `runtime_dom_audit` as `pending-browser-open` until a
browser opens the deck.

## Recovery behavior

- Every run increments `revision` in the state file.
- A failed run writes `needs_revision` and preserves the exact error.
- Correct the reported artifact and run the same command again.
- Stable `deck_id` and `slide_id` values keep presenter notes and page-targeted edits
  attached across revisions.
- `references/pipeline-state-schema-v1.json` is the machine-readable state contract for
  future CLI, Web, API, and MCP clients.
