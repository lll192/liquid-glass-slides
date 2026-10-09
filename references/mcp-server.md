# MCP server

`scripts/mcp_server.py` exposes the presentation engine as a local MCP server over
standard input/output. It uses only the Python standard library and delegates every
operation to `scripts/slides.py`, so CLI and MCP clients share the same validation,
response envelope, and production behavior.

## Tools

| Tool | Purpose |
|---|---|
| `slides_doctor` | Check installation and discover capabilities |
| `slides_validate` | Validate an outline, brief, or source manifest |
| `slides_build` | Build one self-contained HTML deck |
| `slides_run` | Run the recoverable production pipeline |
| `slides_status` | Read a pipeline state |
| `slides_mark_exported` | Record successful delivery |

Tool results include both MCP text content and `structuredContent` using the Agent CLI
response envelope. Validation or production failures set `isError: true` without breaking
the MCP connection.

## Resources

A newly connected agent can read the core contracts without knowing the repository layout:

- `slides://schema/deck-v2` — machine-readable outline contract.
- `slides://schema/agent-response-v1` — structured CLI/MCP result contract.
- `slides://instructions` — model-neutral production workflow.
- `slides://layouts` — current semantic layout identifiers.

## File boundary

The server only reads and writes paths inside the directory passed with `--workspace`.
Relative tool paths resolve from that directory. Attempts to escape through `..` or an
absolute path outside the boundary fail as invalid parameters.

Choose a project directory that contains the outline, sources, images, and desired output
folder. Do not point the boundary at an entire drive or user profile.

## Generic MCP client configuration

Replace both paths with absolute paths on the local machine:

```json
{
  "mcpServers": {
    "liquid-glass-slides": {
      "command": "python",
      "args": [
        "C:/path/to/liquid-glass-slides/scripts/mcp_server.py",
        "--workspace",
        "C:/path/to/presentation-project"
      ]
    }
  }
}
```

Clients that use TOML can express the same process configuration as:

```toml
[mcp_servers.liquid-glass-slides]
command = "python"
args = [
  "C:/path/to/liquid-glass-slides/scripts/mcp_server.py",
  "--workspace",
  "C:/path/to/presentation-project"
]
```

Restart or reload the AI client after adding the server. The client should discover six
`slides_*` tools. Run `slides_doctor` first, then `slides_validate` before build or production.

## Protocol behavior

- Transport: newline-delimited JSON-RPC 2.0 over stdio.
- Protocol versions: modern `2026-07-28` plus legacy `2024-11-05`, `2025-03-26`, `2025-06-18`, and `2025-11-25`.
- Capabilities: tools and read-only resources, with stable lists for the life of the process.
- Lifecycle: modern clients use `server/discover` and self-describing request metadata without a session; legacy clients use `initialize` and `notifications/initialized`.
- Modern list/read results include `ttlMs` and `cacheScope`; modern responses identify the server in `_meta`.
- Server stdout contains protocol messages only. Human diagnostics never leak into stdout.

The MCP adapter intentionally provides local deterministic production. Image generation,
web research, publishing, and other external side effects remain the responsibility of the
calling agent and require their own permissions.
