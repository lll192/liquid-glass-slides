# HTTP API

`scripts/api_server.py` exposes the same Agent Service used by CLI and MCP through an
authenticated JSON API. It uses only the Python standard library.

## Start locally

```bash
python scripts/api_server.py \
  --workspace C:/path/to/presentation-project \
  --host 127.0.0.1 \
  --port 8765
```

When `--token` is omitted, the server generates a strong bearer token and prints it to
standard error. Keep that terminal open. The API never writes the token into the project.

For a fixed development token:

```bash
python scripts/api_server.py --workspace C:/project --token local-development-token
```

## Endpoints

| Method | Path | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/health` | No | Liveness check |
| `GET` | `/openapi.json` | No | OpenAPI 3.1 description |
| `GET` | `/v1/capabilities` | Bearer | Engine self-check and capability discovery |
| `POST` | `/v1/validate` | Bearer | Validate a brief, manifest, or outline |
| `POST` | `/v1/build` | Bearer | Build a self-contained HTML deck |
| `POST` | `/v1/run` | Bearer | Run the recoverable production pipeline |
| `POST` | `/v1/status` | Bearer | Read pipeline state |
| `POST` | `/v1/mark-exported` | Bearer | Record successful delivery |

POST bodies use the same argument names as `references/agent-cli.md`. Example:

```json
{
  "outline": "outline.json",
  "output": "dist/deck.html"
}
```

Paths may be relative to the configured workspace or absolute paths inside it. Paths that
leave the workspace are rejected.

## PowerShell example

```powershell
$headers = @{ Authorization = "Bearer local-development-token" }
$body = @{ outline = "outline.json"; output = "dist/deck.html" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8765/v1/build" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

## Status codes

- `200`: operation completed.
- `400`: malformed request, unreadable input, invalid path, or system-level failure.
- `401`: missing or incorrect bearer token.
- `404`: unknown route.
- `422`: readable input needs revision, such as schema validation errors.

Every operation response uses the Agent CLI envelope. HTTP status communicates transport
outcome; `ok`, `errors`, and `warnings` communicate product outcome.

## Security

- The default host is `127.0.0.1`.
- Binding to another interface requires `--allow-remote`.
- Bearer authentication is always active.
- Request bodies are limited to 1 MiB.
- API responses disable caching and content-type sniffing.
- Files remain inside the explicit workspace boundary.
- The built-in server does not provide TLS. For remote use, place it behind an authenticated
  TLS reverse proxy and a trusted firewall. Never expose it directly to the public internet.

This API performs deterministic local presentation production. External research, image
generation, publishing, and cloud storage remain separate, explicitly authorized actions.
