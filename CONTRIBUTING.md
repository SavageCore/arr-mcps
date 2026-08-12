# Contributing

This repository is an index and working tree for a set of independently-versioned
[MCP](https://modelcontextprotocol.io) servers. Each MCP has its own repository
and its own release lifecycle; this repo only tracks its own files.

## Adding a new MCP

1. Create the working copy as its own git repo:
   ```bash
   cd ~/Git/arr-mcps
   cp -r tracearr-mcp <service>-mcp
   rm -rf <service>-mcp/.git
   cd <service>-mcp
   git init -b main
   ```
2. Follow [`steps.md`](steps.md) end-to-end: build, first release (bump, tag, push),
   then self-register in `README.md`.
3. Use `tracearr-mcp/` as the template — mirror its Makefile, `release.yml` workflow,
   test patterns, and AGENTS.md conventions. Keep the server single-file unless
   it clearly outgrows that.

The `<service>-mcp` subfolders are gitignored (`/*-mcp/`), so the masterlist
repo never tracks their contents.

## Commit style

Use [conventional commits](https://www.conventionalcommits.org) with a single
short summary line, e.g. `feat: add <service>-mcp` or `docs: update qui-mcp entry`.

Default branch is `main`.