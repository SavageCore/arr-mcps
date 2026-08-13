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

import json
from dataclasses import dataclass
from pathlib import Path

# Persistence for user-saved custom profiles. Lives next to the wizard's other
# config so it survives reinstalls and is shared across hosts.
CUSTOM_PROFILES_DIR = Path.home() / ".config" / "profile-mcp"
CUSTOM_PROFILES_FILE = CUSTOM_PROFILES_DIR / "profiles.json"

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
    # When set, the profile stores concrete config keys verbatim (a saved
    # custom profile) instead of roles that resolve per host.
    keys: tuple[str, ...] | None = None


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
    if profile.keys is not None:
        return list(profile.keys)
    keys = []
    for role in profile.roles:
        key = resolve_key(role, host)
        if key:
            keys.append(key)
    return keys


BUILTIN_NAMES = frozenset(p.name for p in PROFILES)


def load_custom_profiles() -> dict[str, list[str]]:
    """Return {name: [server keys, ...]} for user-saved custom profiles."""
    try:
        data = json.loads(CUSTOM_PROFILES_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        name: [k for k in keys if isinstance(k, str)]
        for name, keys in data.items()
        if isinstance(name, str) and isinstance(keys, list)
    }


def save_custom_profile(name: str, keys: list[str]) -> None:
    """Persist a custom profile; overwrites any existing profile with the name."""
    profiles = load_custom_profiles()
    profiles[name] = keys
    CUSTOM_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_PROFILES_FILE.write_text(json.dumps(profiles, indent=2) + "\n")


# Provider sets: which models back the plan / build / heavy agents for a
# session. Applied as an `agent` block in the OPENCODE_CONFIG_CONTENT
# override alongside the MCP profile, so switching provider needs no config
# rewrite on disk.
MODEL_SETS: dict[str, dict[str, str]] = {
    "free": {
        "desc": "Zen free tier — no spend",
        "plan": "opencode/glm-5-free",
        "build": "opencode/deepseek-v4-flash-free",
        "heavy": "opencode/nemotron-3-ultra-free",
    },
    "go": {
        "desc": "opencode Go subscription",
        "plan": "opencode-go/glm-5.2",
        "build": "opencode-go/deepseek-v4-flash",
        "heavy": "opencode-go/gpt-5.6-luna",
    },
    # Cheap Go set: flash for both plan and build, and no heavy agent at all.
    # Omitting the "heavy" key means the wizard disables the heavy agent for
    # the session (see build_config in cli.py) instead of pinning an expensive
    # model to it.
    "go-cheap": {
        "desc": "opencode Go subscription — flash plan & build, no heavy",
        "plan": "opencode-go/deepseek-v4-flash",
        "build": "opencode-go/deepseek-v4-flash",
    },
    "deepseek": {
        "desc": "DeepSeek direct API",
        "plan": "deepseek/deepseek-v4-pro",
        "build": "deepseek/deepseek-v4-flash",
        "heavy": "deepseek/deepseek-v4-pro",
    },
}

# Which model sets each host may use. The Proxmox box has no paid account, so
# it only offers the free tier; the desktop host can use every set. Hosts not
# listed fall back to all sets.
HOST_MODEL_SETS: dict[str, tuple[str, ...]] = {
    "desktop": ("free", "go", "go-cheap", "deepseek"),
    "proxmox": ("free",),
}


def model_sets_for_host(host: str) -> dict[str, dict[str, str]]:
    """Return the model sets offered on the given host."""
    names = HOST_MODEL_SETS.get(host, tuple(MODEL_SETS))
    return {name: MODEL_SETS[name] for name in names if name in MODEL_SETS}