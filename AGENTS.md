# AGENTS.md — arr-mcps

Monorepo of MCP servers for the arr stack and adjacent services: `bookshelf-mcp`,
`cleanuparr-mcp`, `dashbrr-mcp`, `komga-mcp`, `mylar3-mcp`, `profilarr-mcp`,
`prowlarr-mcp`, `qbittorrent-mcp`, `qui-mcp`, `radarr-mcp`, `seerr-mcp`,
`sonarr-mcp`, `tracearr-mcp`. `tracearr-mcp` is the reference/template base
for new servers (see "Tool design standard" below — it's also the standard
every server here now follows).

Each server is a separate FastMCP project with its own `pyproject.toml`,
`uv.lock`, and `Makefile`.

## Tool design standard: portmanteau tools, not one-per-endpoint

**Expose ~5-15 resource-scoped tools per server, never one MCP tool per REST
endpoint.** Each tool takes an `operation` string (typed `Literal[...]` of
the real operation names) plus an `arguments` dict, and dispatches to the
underlying per-endpoint function by name. This is not optional — a server
registering one tool per endpoint injects hundreds of tool schemas into every
session's system prompt before the first user message, at roughly 200-500
tokens per tool. The fleet here used to do exactly that (up to 461 tools in
one server) and it made every session on the deploying host auto-compact
before any work could start.

Concretely, in each `<svc>_mcp.py`:
- Keep every per-endpoint function as a plain (non-decorated) async callable
  — same signature, docstring, and body as before. Don't touch what it does.
- Define `_GROUPS: dict[str, tuple[str, ...]]` bucketing every endpoint
  function name into one of ~5-15 resource groups (e.g. `<svc>_queue`,
  `<svc>_config`). The ceiling is on the number of *groups* (MCP tools), not
  operations per group — one group legitimately holding 40+ operations is
  fine and normal.
- Register exactly one MCP tool per group: a `dispatch(operation, arguments)`
  closure that looks up the right function by name and calls
  `await fn(**(arguments or {}))`. Use `Tool.from_function(dispatch, name=group,
  description=..., annotations=ann)`, with the description listing every
  operation's signature and one-line doc so an LLM doesn't need a discovery
  round-trip.
- Mark a group `readOnlyHint=True` only when every operation in it was
  originally read-only; mixed groups carry no hints.
- Add a test asserting every endpoint function name appears in exactly one
  `_GROUPS` entry (name it `test_all_*_grouped` or similar) — this is the
  safety net that catches an endpoint silently falling out of the tool
  surface during a refactor.
- If any operation can return something other than a JSON object/array (raw
  text, base64, a bare int, `None`), widen `dispatch`'s return type
  accordingly (`JSONVal | str`, `| int`, `| None`, ...) — FastMCP validates
  the declared return type against what's actually returned, and a too-narrow
  union breaks structured-content validation for those operations at runtime.

`tracearr-mcp/tracearr_mcp.py` is what new servers are scaffolded from (via
the `new-mcp` wizard in `bin/`). It is deliberately left at its original
one-tool-per-endpoint shape — at 13 tools it's already under the ceiling, so
converting it would add indirection for no context-budget benefit — but
`bin/new_mcp/templates.py::PLAN_PROMPT`, the brief handed to the scaffolding
agent for *new* servers, must state this standard explicitly (it previously
said "full coverage of API read and writes" with no grouping instruction,
which is exactly what produced the 200+-tool servers this standard exists to
prevent). See any refactored server's `AGENTS.md` (e.g. `sonarr-mcp/AGENTS.md`)
for a worked example with real numbers, and `sandraschi/arr-mcp` (a separate,
unrelated repo — read-only reference, not part of this fleet) for the
independently-arrived-at pattern this one converged on.

## Release workflow (applies to every MCP here)
1. Use the repo's `make bump-*` target (`uv version --bump patch|minor|major`)
   — it updates `pyproject.toml` **and** `uv.lock` together. Never hand-edit the
   version.
2. Commit message is **just the version**, e.g. `0.1.2`. No prefixes, no bodies.
3. Tag it `v<version>` (e.g. `v0.1.2`).
4. Push main and the tag:
   ```
   git push origin main
   git push origin v<version>
   ```
5. If a copy of the server is used by opencode under
   `/home/savagecore/Documents/christopfarr/mcp/<name>`, sync it:
   ```
   cd /home/savagecore/Documents/christopfarr/mcp/<name>
   git fetch origin && git reset --hard origin/main
   ```
6. If the server is deployed to the Proxmox host (`192.168.50.3`, root SSH
   key), pull the repo there and refresh the tool:
   ```
   ssh root@192.168.50.3 -- 'cd /root/<name> && git fetch origin && git reset --hard origin/main'
   ssh root@192.168.50.3 -- 'cd /root/<name> && uv tool install --force .'
   ```
   Hosts run MCPs via `uv tool install` → `/root/.local/bin/<name>`, wired into
   `/root/.config/opencode/opencode.jsonc`.

## New-MCP flow
Follow [`steps.md`](steps.md) end-to-end manually: scaffold from
`tracearr-mcp/`, build, release (create repo, bump, tag, push), register in
README, install.

## Per-server AGENTS.md
Each server repo has its own `AGENTS.md` with specifics (tests, live integration
env vars, design notes). Read it before working in that server.

## External MCP deployments

`arr-mcps/qbittorrent-mcp` is deployed alongside the arr-stack servers:

- **Env vars** (set in `opencode.json`/`opencode.jsonc`): `QBITTORRENT_URL`,
  `QBITTORRENT_API_KEY`, plus `QBITTORRENT_USERNAME`/`QBITTORRENT_PASSWORD` as a
  fallback (API key wins if set).
- **Always use the IP from NPM** (`forward_host`/`forward_port`) in
  `QBITTORRENT_URL`, never the duckdns URL — same convention as `qui-mcp`,
  `komga-mcp`, `mylar3-mcp`. Credentials live in the desktop
  `~/Documents/christopfarr/opencode.json` and host
  `/root/.config/opencode/opencode.jsonc` (both gitignored/local — never commit
  them; this repo is public).
