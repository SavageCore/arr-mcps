"""Self-check for MODEL_SETS, build_config's agent block, and custom profiles.
Run: python bin/test_sets.py"""

import tempfile
from pathlib import Path

from profile_mcp.cli import build_config
from profile_mcp.profiles import (
    MODEL_SETS,
    Profile,
    PROFILES,
    load_custom_profiles,
    model_sets_for_host,
    profile_keys,
    save_custom_profile,
)

ROLES = ("plan", "build", "heavy")

for name, s in MODEL_SETS.items():
    for role in ROLES:
        assert role in s, f"{name} missing role {role}"
        provider, _, model = s[role].partition("/")
        assert provider and model, f"{name}.{role} = {s[role]!r} is not 'provider/model'"

config = build_config({}, [], "go")
assert config["agent"]["plan"]["model"] == "opencode-go/glm-5.2"
assert config["agent"]["build"]["model"] == "opencode-go/deepseek-v4-flash"
assert config["agent"]["heavy"]["model"] == "opencode-go/gpt-5.6-luna"
assert set(config["agent"]) == set(ROLES)

# none profile: every server explicitly disabled, nothing enabled
config = build_config({"a": {}, "b": {}}, [], "go")
assert all(v["enabled"] is False for v in config["mcp"].values())

# per-host model sets: proxmox has no paid account -> free only
proxmox_sets = model_sets_for_host("proxmox")
assert set(proxmox_sets) == {"free"}, proxmox_sets
assert set(model_sets_for_host("desktop")) == set(MODEL_SETS)
assert set(model_sets_for_host("unknown-host")) == set(MODEL_SETS)

# custom profiles: persist, reload, overwrite
from profile_mcp import profiles as pmod
with tempfile.TemporaryDirectory() as tmp:
    pmod.CUSTOM_PROFILES_DIR = Path(tmp)
    pmod.CUSTOM_PROFILES_FILE = Path(tmp) / "profiles.json"
    assert load_custom_profiles() == {}
    save_custom_profile("my-stack", ["sonarr-mcp", "radarr-mcp"])
    save_custom_profile("my-stack", ["sonarr-mcp"])
    saved = load_custom_profiles()
    assert saved == {"my-stack": ["sonarr-mcp"]}, saved
    saved_profile = Profile("my-stack", "saved", ("sonarr-mcp",), keys=("sonarr-mcp",))
    assert profile_keys(saved_profile, "desktop") == ["sonarr-mcp"]
    assert profile_keys(PROFILES[0], "desktop")

print("ok")
