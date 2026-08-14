# arr-mcps

A collection of [Model Context Protocol](https://modelcontextprotocol.io) (MCP)
servers for the self-hosted "arr" stack and adjacent media and utility services.

Each MCP lives in its **own repository** with independent versioning and
releases. This repository is an index and a working tree — **not a monorepo** —
so every MCP keeps its own changelog, tags, and GitHub Releases. The per-MCP
working copies live here as gitignored subfolders.

Built with [FastMCP](https://gofastmcp.com). Each server is a single wheel
installed with `uv`, then registered with your MCP client.

Every server here exposes ~5-15 resource-scoped tools rather than one tool
per REST endpoint — each tool takes an `operation` parameter plus an
`arguments` dict, so the full API surface stays available without injecting
hundreds of tool schemas into your MCP client's context on every session.
See a server's own README (e.g. [sonarr-mcp](https://github.com/SavageCore/sonarr-mcp))
for its exact tool-to-operation mapping.

## Media servers

### [bookshelf-mcp](https://github.com/SavageCore/bookshelf-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/bookshelf-mcp)](https://github.com/SavageCore/bookshelf-mcp/releases/latest)

MCP server for [Bookshelf](https://github.com/pennydreadful/bookshelf) — read
and manage your book library: authors, books, editions, series, files, the
download queue, history, indexers, import lists, custom formats, tags, and more
(v1 REST API surface).

```bash
uv tool install bookshelf_mcp-*.whl
claude mcp add bookshelf --env BOOKSHELF_URL=... --env BOOKSHELF_API_KEY=... -- bookshelf-mcp
```

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

### [radarr-mcp](https://github.com/SavageCore/radarr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/radarr-mcp)](https://github.com/SavageCore/radarr-mcp/releases/latest)

MCP server for [Radarr](https://radarr.video) — read and manage your movie
library: movies, files, queue, history, indexers, import lists, custom formats,
and more (v3 API surface).

```bash
uv tool install radarr_mcp-*.whl
claude mcp add radarr --env RADARR_URL=... --env RADARR_API_KEY=... -- radarr-mcp
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

### [prowlarr-mcp](https://github.com/SavageCore/prowlarr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/prowlarr-mcp)](https://github.com/SavageCore/prowlarr-mcp/releases/latest)

MCP server for [Prowlarr](https://github.com/Prowlarr/Prowlarr) — manage your
indexers, applications, download clients, indexer proxies, notifications, tags,
and custom filters. Run cross-indexer searches and system commands (v1 API surface).

```bash
uv tool install prowlarr_mcp-*.whl
claude mcp add prowlarr --env PROWLARR_URL=... --env PROWLARR_API_KEY=... -- prowlarr-mcp
```

### [seerr-mcp](https://github.com/SavageCore/seerr-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/seerr-mcp)](https://github.com/SavageCore/seerr-mcp/releases/latest)

MCP server for [Seerr](https://github.com/seerr-team/seerr) — search and
manage media requests, approvals, users, issues, watchlists, and settings (v1
REST API surface).

```bash
uv tool install seerr_mcp-*.whl
claude mcp add seerr --env SEERR_URL=... --env SEERR_API_KEY=... -- seerr-mcp
```

## Download clients

### [qbittorrent-mcp](https://github.com/SavageCore/qbittorrent-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/qbittorrent-mcp)](https://github.com/SavageCore/qbittorrent-mcp/releases/latest)

MCP server for [qBittorrent](https://github.com/qbittorrent/qBittorrent) — manage torrents, categories, tags, RSS, search, and the WebUI API v2.

```bash
uv tool install qbittorrent_mcp-*.whl
claude mcp add qbittorrent --env QBITTORRENT_URL=... --env QBITTORRENT_API_KEY=... -- qbittorrent-mcp
```

### [qbit_manage-mcp](https://github.com/SavageCore/qbit_manage-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/qbit_manage-mcp)](https://github.com/SavageCore/qbit_manage-mcp/releases/latest)

MCP server for [qbit_manage](https://github.com/StuffAnThings/qbit_manage) —
run maintenance commands against your qBittorrent torrents, manage config
files, the scheduler, logs, security settings, and system state.

```bash
uv tool install qbit_manage_mcp-*.whl
claude mcp add qbit-manage --env QBIT_MANAGE_URL=... --env QBIT_MANAGE_API_KEY=... -- qbit-manage-mcp
```

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

See [`steps.md`](steps.md) — it covers the full flow end-to-end, from
scaffolding the new MCP off `tracearr-mcp/` to releasing it, self-registering
it in this README, and installing it locally and on the server. The per-MCP
subfolders are gitignored, so the masterlist only ever tracks its own files.

## License

MIT — see [LICENSE](LICENSE). Each child MCP repository carries its own MIT
license.
