# Contributing

This repository is an index and working tree for a set of independently-versioned
[MCP](https://modelcontextprotocol.io) servers. Each MCP has its own repository
and its own release lifecycle; this repo only tracks its own files.

## Adding a new MCP

Use the `new-mcp` wizard:
```bash
new-mcp https://github.com/Sonarr/Sonarr
```

It scaffolds from `tracearr-mcp/`, builds, releases, registers in README, and installs.
The template (`tracearr-mcp/`) defines all Makefile, `release.yml` workflow, test patterns,
and AGENTS.md conventions — keep new servers single-file unless they clearly outgrow it.

**Expose ~5-15 resource-scoped portmanteau tools, not one MCP tool per REST
endpoint** — see `AGENTS.md`'s "Tool design standard" for the full pattern
(an `operation`-enum dispatcher per resource group, endpoint functions kept
as plain callables looked up by name). A server that registers one tool per
endpoint blows the MCP context budget on every session's first message; this
is the single most important convention in this repo, and the wizard's own
planning prompt (`bin/new_mcp/templates.py::PLAN_PROMPT`) must keep steering
toward it for any service with a non-trivial API surface.

The `<service>-mcp` subfolders are gitignored (`/*-mcp/`), so the masterlist
repo never tracks their contents.

## Commit style

Use [conventional commits](https://www.conventionalcommits.org) with a single
short summary line, e.g. `feat: add <service>-mcp` or `docs: update qui-mcp entry`.

Default branch is `main`.