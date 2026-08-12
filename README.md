# arr-mcps

A collection of [Model Context Protocol](https://modelcontextprotocol.io) (MCP)
servers for the self-hosted "arr" stack and adjacent media and utility services.

Each MCP lives in its **own repository** with independent versioning and
releases. This repository is an index and a working tree — **not a monorepo** —
so every MCP keeps its own changelog, tags, and GitHub Releases. The per-MCP
working copies live here as gitignored subfolders.

Built with [FastMCP](https://gofastmcp.com). Each server is a single wheel
installed with `uv`, then registered with your MCP client.

## Media servers

### [komga-mcp](https://github.com/SavageCore/komga-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/komga-mcp)](https://github.com/SavageCore/komga-mcp/releases/latest)

MCP server for [Komga](https://github.com/gotson/komga) — browse and manage
comic, manga, BD, and ebook libraries (writes gated to the admin role).

```bash
uv tool install komga_mcp-*.whl
claude mcp add komga --env KOMGA_URL=... --env KOMGA_API_KEY=... -- komga-mcp
```

### [mylar3-mcp](https://github.com/SavageCore/mylar3-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/mylar3-mcp)](https://github.com/SavageCore/mylar3-mcp/releases/latest)

MCP server for [Mylar3](https://github.com/MylarComics/mylar3) — comic book
manager: watchlist, wanted issues, pull-list/upcoming, history, logs, story
arcs, and providers.

```bash
uv tool install mylar3_mcp-*.whl
claude mcp add mylar3 --env MYLAR_URL=... --env MYLAR_API_KEY=... -- mylar3-mcp
```

## Arr stack helpers

### [cleanuparr-mcp](https://github.com/SavageCore/cleanuparr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/cleanuparr-mcp)](https://github.com/SavageCore/cleanuparr-mcp/releases/latest)

MCP server for [Cleanuparr](https://github.com/Cleanuparr/Cleanuparr) — inspect
status, history, statistics, jobs, and configuration of your arr stack cleanup.

```bash
uv tool install cleanuparr_mcp-*.whl
claude mcp add cleanuparr --env CLEANUPARR_URL=... --env CLEANUPARR_API_KEY=... -- cleanuparr-mcp
```

### [profilarr-mcp](https://github.com/SavageCore/profilarr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/profilarr-mcp)](https://github.com/SavageCore/profilarr-mcp/releases/latest)

MCP server for [Profilarr](https://github.com/Dictionarry-Hub/Profilarr) —
manage linked databases, connected Radarr/Sonarr instances, backups, jobs,
announcements, and system status (v1 REST API surface).

```bash
uv tool install profilarr_mcp-*.whl
claude mcp add profilarr --env PROFILARR_URL=... --env PROFILARR_API_KEY=... -- profilarr-mcp
```

## Download clients

### [qui-mcp](https://github.com/SavageCore/qui-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/qui-mcp)](https://github.com/SavageCore/qui-mcp/releases/latest)

MCP server for [qui](https://github.com/autobrr/qui) — monitor and manage
qBittorrent instances, torrents, automations, cross-seeding, RSS, backups, and
related services.

```bash
uv tool install qui_mcp-*.whl
claude mcp add qui --env QUI_URL=... --env QUI_API_KEY=... -- qui-mcp
```

## Monitoring

### [dashbrr-mcp](https://github.com/SavageCore/dashbrr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/dashbrr-mcp)](https://github.com/SavageCore/dashbrr-mcp/releases/latest)

MCP server exposing the [Dashbrr](https://github.com/autobrr/dashbrr) REST API as tools, so an LLM can read and manage your dashbrr instance.

```bash
uv tool install dashbrr_mcp-*.whl
claude mcp add dashbrr --env DASHBRR_URL=... --env DASHBRR_API_KEY=... -- dashbrr-mcp
```


### [tracearr-mcp](https://github.com/SavageCore/tracearr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/tracearr-mcp)](https://github.com/SavageCore/tracearr-mcp/releases/latest)

MCP server for [Tracearr](https://docs.tracearr.com/api) — read-only
Plex/Jellyfin/Emby monitoring: watch history, active streams, media, users,
libraries, and recently added items.

```bash
uv tool install tracearr_mcp-*.whl
claude mcp add tracearr --env TRACEARR_URL=... --env TRACEARR_API_KEY=... -- tracearr-mcp
```

## Adding a new MCP

See [`new.md`](new.md) for the full prompt template and [`bin/new-mcp`](bin/new-mcp)
for the end-to-end pipeline that orchestrates it. Use `tracearr-mcp/` as the
base — mirror its Makefile, release workflow, test patterns, and AGENTS.md
conventions. After the first release, self-register the new MCP by adding an
entry to this README in the appropriate category and committing to this
repository. The per-MCP subfolders are gitignored, so the masterlist only ever
tracks its own files.

To stand up a new MCP:

```bash
bin/new-mcp all <service> --repo <upstream-user>/<upstream-repo>
```

It scaffolds from `tracearr-mcp/`, prints the Plan prompt for you to run in
opencode, then (once you've committed the initial build) does release →
register → install, each with a `[Y/n]` gate. See `bin/new-mcp --help` for the
individual `scaffold`/`release`/`register`/`install` stages.

## License

MIT — see [LICENSE](LICENSE). Each child MCP repository carries its own MIT
license.
