# AGENTS.md — arr-mcps

Monorepo of MCP servers for the arr stack: `cleanuparr-mcp`, `dashy-mcp`,
`komga-mcp`, `mylar3-mcp`, `profilarr-mcp`, `qui-mcp`, `tracearr-mcp`.

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

## Per-server AGENTS.md
Each server repo has its own `AGENTS.md` with specifics (tests, live integration
env vars, design notes). Read it before working in that server.
