# AGENTS.md — arr-mcps

Monorepo of MCP servers for the arr stack: `cleanuparr-mcp`, `komga-mcp`,
`mylar3-mcp`, `profilarr-mcp`, `qui-mcp`, `tracearr-mcp`. `tracearr-mcp` is the
reference/template base for new servers.

Each server is a separate FastMCP project with its own `pyproject.toml`,
`uv.lock`, and `Makefile`.

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
Follow [`new.md`](new.md) end-to-end manually: scaffold from `tracearr-mcp/`,
build, release (create repo, bump, tag, push), register in README, install.

## Per-server AGENTS.md
Each server repo has its own `AGENTS.md` with specifics (tests, live integration
env vars, design notes). Read it before working in that server.

## External MCP deployments

`SavageCore/qbittorrent-mcp` is deployed alongside the arr-stack servers:

- **Env vars** (set in `opencode.json`/`opencode.jsonc`): `QBITTORRENT_URL`,
  `QBITTORRENT_API_KEY`, plus `QBITTORRENT_USERNAME`/`QBITTORRENT_PASSWORD` as a
  fallback (API key wins if set).
- **Always use the IP from NPM** (`forward_host`/`forward_port`) in
  `QBITTORRENT_URL`, never the duckdns URL — same convention as `qui-mcp`,
  `komga-mcp`, `mylar3-mcp`. Credentials live in the desktop
  `~/Documents/christopfarr/opencode.json` and host
  `/root/.config/opencode/opencode.jsonc` (both gitignored/local — never commit
  them; this repo is public).
