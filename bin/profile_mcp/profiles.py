"""Profile registry and host/role resolution for the profile-mcp wizard.

A *profile* is a named subset of MCP servers. The wizard discovers the full
server list from the host's global opencode config, then emits a project-scoped
config that explicitly toggles `enabled` on every known server so only the
chosen subset loads in that session.

Server keys differ slightly between the desktop config and the proxmox host, so
profiles reference *roles* (canonical names) which resolve to the actual config
key per host.
"""

from __future__ import annotations

from dataclasses import dataclass

# Role -> (desktop key, proxmox key). Only roles whose key differs across hosts
# need an entry; the same key on both hosts is omitted here.
ROLE_KEYS: dict[str, dict[str, str]] = {
    "npm": {"desktop": "nginx-proxy-manager", "proxmox": "nginx-proxy-manager-mcp"},
    "opnsense": {"desktop": "opnsense", "proxmox": "opnsense-mcp"},
    "prowlarr": {"desktop": "prowlarr-mcp", "proxmox": "prowlarr"},
}

# Shared roles whose config key is identical on both hosts.
SAME_KEY_ROLES = {
    "dashy": "dashy-mcp",
    "proxmox": "proxmox-mcp-plus",
    "qbittorrent": "qbittorrent-mcp",
    "jellyfin": "jellyfin-mcp",
    "tracearr": "tracearr-mcp",
    "netdata": "netdata",
    "dashbrr": "dashbrr-mcp",
    "radarr": "radarr-mcp",
    "sonarr": "sonarr-mcp",
    "seerr": "seerr-mcp",
    "bookshelf": "bookshelf-mcp",
    "komga": "komga-mcp",
    "mylar3": "mylar3-mcp",
    "lidarr": "lidarr-mcp",
    "cleanuparr": "cleanuparr-mcp",
    "profilarr": "profilarr-mcp",
    "qui": "qui-mcp",
}


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    roles: tuple[str, ...]


PROFILES: list[Profile] = [
    Profile(
        name="deploy",
        description="Spin up a new arrstack item (reverse proxy, firewall, VM, indexer sync, dashboard)",
        roles=("npm", "opnsense", "proxmox", "prowlarr", "dashy"),
    ),
    Profile(
        name="media",
        description="Request and debug media: TV (sonarr), movies (radarr), books, manga, comics, music",
        roles=(
            "radarr",
            "sonarr",
            "prowlarr",
            "seerr",
            "bookshelf",
            "komga",
            "mylar3",
            "lidarr",
        ),
    ),
    Profile(
        name="diagnostics",
        description="Troubleshoot stack health and download activity",
        roles=("tracearr", "jellyfin", "qbittorrent", "netdata", "dashbrr"),
    ),
]


def resolve_key(role: str, host: str) -> str | None:
    """Return the config key for a role on the given host, or None if unknown."""
    if role in ROLE_KEYS:
        return ROLE_KEYS[role].get(host)
    return SAME_KEY_ROLES.get(role)


def role_key_map(host: str) -> dict[str, str]:
    """Map every known role to its config key for the host."""
    mapping: dict[str, str] = {}
    for role, keys in ROLE_KEYS.items():
        key = keys.get(host)
        if key:
            mapping[role] = key
    for role, key in SAME_KEY_ROLES.items():
        mapping[role] = key
    return mapping


def profile_keys(profile: Profile, host: str) -> list[str]:
    """Resolve a profile's roles to concrete config keys present on the host."""
    keys = []
    for role in profile.roles:
        key = resolve_key(role, host)
        if key:
            keys.append(key)
    return keys