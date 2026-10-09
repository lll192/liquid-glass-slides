# Content Director

Content Director is the deterministic editorial layer between an authored v2 outline
and rendering. It diagnoses whether the deck can be understood and delivered as a
story, but it does not invent facts, numbers, quotations, or source claims.

## Run it directly

```bash
python scripts/content_director.py outline.json --report director-report.json
```

The report contains a deck score, coverage metrics, deck-level warnings, and one entry
per stable `slide_id`. Each page entry separates observable `findings` from concrete
`recommendations`. The score is a workflow signal, not a measure of factual quality.

The director checks:

- whether substantive pages have one main point;
- whether story roles are explicit and sufficiently varied;
- whether pages connect through natural transitions;
- whether substantive pages contain usable speaker notes;
- whether meaningful visuals support enough content pages;
- whether dense display copy should move into notes or another page.

## Safe metadata completion

```bash
python scripts/content_director.py outline.json --apply-safe outline-directed.json
```

This mode writes a new outline and may fill only information already implied by the
existing structure:

- inferred `story_role` and `emotion`;
- a claim-like title copied into a missing `main_point`;
- a `visual_plan` describing an information visual already present on the page.

It never writes speaker prose, changes visible copy, fabricates chart data, converts a
layout, or overwrites the input file. Recommendations that require editorial judgment
remain in the report for a human or capable AI to resolve.

## Visual recommendations

A text-only content page receives one semantic recommendation such as comparison,
process flow, concept map, image, or data visualization. A data-visualization suggestion
is explicitly marked `requires_source_check`; numbers must be traceable before a chart
or table is created. Decorative ripple and Three.js atmosphere never count as evidence.

The recoverable production pipeline runs Content Director automatically and writes
`<deck>.director-report.json`. It also embeds the report in the QA artifact so Web, API,
MCP, and other AI clients can expose the same diagnosis without parsing console text.
