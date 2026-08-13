"""Command-line interface for the profile-mcp wizard."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from profile_mcp import __version__
from profile_mcp.profiles import PROFILES, role_key_map, profile_keys

console = Console()

DESKTOP_GLOBAL = Path.home() / "Documents" / "christopfarr" / "opencode.json"
PROXMOX_GLOBAL = Path("/root/.config/opencode/opencode.jsonc")


def detect_host(global_path: Path) -> str:
    if global_path == PROXMOX_GLOBAL or str(global_path).startswith("/root"):
        return "proxmox"
    return "desktop"


def strip_jsonc_comments(text: str) -> str:
    """Remove // and /* */ comments, keeping anything inside string literals."""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\":
                i += 1
                if i < n:
                    out.append(text[i])
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def load_mcp_keys(global_path: Path) -> dict[str, dict]:
    """Load the global config and return {server_key: server_dict} for its mcp block."""
    try:
        text = global_path.read_text()
    except OSError:
        return {}
    try:
        if global_path.suffix.lower() == ".jsonc":
            text = strip_jsonc_comments(text)
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    mcp = data.get("mcp", {})
    return {k: v for k, v in mcp.items() if isinstance(v, dict)}


def print_header():
    header = Text()
    header.append("⚙️  ", style="bold cyan")
    header.append("profile-mcp", style="bold cyan")
    header.append(" — Choose which MCP servers to load", style="dim cyan")

    console.print()
    console.print(header)
    console.print()

    info = (
        "Generates a project-scoped opencode config that loads only the "
        "MCP servers you need for the task at hand.\n\n"
        "[dim]→ Pick a named profile (deploy / media / diagnostics)[/dim]\n"
        "[dim]→ Or build a custom set of servers[/dim]\n"
        "[dim]→ A <profile>/opencode.json is written; launch opencode there[/dim]"
    )
    console.print(Panel(info, border_style="cyan"))
    console.print()


def pick_profile(host: str, available: list[str]) -> tuple[str, list[str]]:
    """Return (label, enabled_server_keys) for a named profile or custom set."""
    table = Table(title="Profiles", show_header=True)
    table.add_column("#", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Servers", style="dim")

    for i, p in enumerate(PROFILES, 1):
        table.add_row(str(i), p.name, p.description, ", ".join(p.roles))
    table.add_row("c", "custom", "Pick exactly the servers you want", "manual")

    console.print(table)
    console.print()

    choice = Prompt.ask(
        "[bold cyan]Choose a profile[/bold cyan]",
        default="1",
        show_default=False,
    ).strip().lower()

    if choice == "c":
        return "custom", choose_custom(available)

    try:
        profile = PROFILES[int(choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice, using 'deploy'.[/red]")
        profile = PROFILES[0]
    enabled = [k for k in profile_keys(profile, host) if k in available]
    return profile.name, enabled


def choose_custom(available: list[str]) -> list[str]:
    """Multi-select (comma-separated toggling) of available server keys."""
    console.print("[bold]Available servers[/bold]")
    for i, key in enumerate(available, 1):
        console.print(f"  [cyan]{i:>2}[/cyan]  {key}")
    console.print()
    selected: set[str] = set()
    while True:
        toggles = Prompt.ask(
            "[cyan]Enter numbers to toggle (blank to finish)[/cyan]",
            default="",
            show_default=False,
        ).strip()
        if not toggles:
            break
        for tok in toggles.replace(",", " ").split():
            try:
                key = available[int(tok) - 1]
            except (ValueError, IndexError):
                console.print(f"[yellow]Ignoring invalid: {tok}[/yellow]")
                continue
            if key in selected:
                selected.discard(key)
                console.print(f"  [dim]- {key}[/dim]")
            else:
                selected.add(key)
                console.print(f"  [green]+ {key}[/green]")
    return sorted(selected)


def build_config(all_keys: dict[str, dict], enabled: list[str]) -> dict:
    """Carry every server's full definition, toggling `enabled` on each.

    The definitions must be included inline (not just `enabled` flags): the
    profile is injected via OPENCODE_CONFIG_CONTENT, and when opencode runs
    outside the config's home directory the server definitions aren't loaded
    from any project config — so they must travel with the override.
    """
    enabled_set = set(enabled)
    mcp = {}
    for key, server in all_keys.items():
        mcp[key] = {**server, "enabled": key in enabled_set}
    return {"$schema": "https://opencode.ai/config.json", "mcp": mcp}


def write_config(config: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "opencode.json"
    out_file.write_text(json.dumps(config, indent=2) + "\n")
    return out_file


def main():
    parser = argparse.ArgumentParser(
        prog="profile-mcp",
        description="Choose which MCP servers opencode loads for a session",
        add_help=False,
    )
    parser.add_argument("--global-config", default=None,
                        help="Path to the global config that defines all MCP servers")
    parser.add_argument("--host", choices=["desktop", "proxmox"], default=None,
                        help="Host whose server keys to use (auto-detected otherwise)")
    parser.add_argument("--dir", default=None,
                        help="Output directory for the generated config")
    parser.add_argument("--non-interactive", metavar="PROFILE", default=None,
                        help="Skip prompts; use a named profile (deploy|media|diagnostics)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    global _HOST
    if args.version:
        console.print(f"profile-mcp v{__version__}")
        return 0

    if args.help:
        console.print("profile-mcp - choose which MCP servers to load")
        console.print("  profile-mcp                       Interactive profile picker")
        console.print("  profile-mcp --non-interactive deploy   Generate the 'deploy' profile")
        console.print("  profile-mcp --host proxmox        Target the proxmox host's server keys")
        console.print("  profile-mcp --dir /path           Write the config elsewhere")
        return 0

    print_header()

    # Resolve global config path
    global_path = Path(args.global_config) if args.global_config else (
        DESKTOP_GLOBAL if DESKTOP_GLOBAL.exists() else PROXMOX_GLOBAL
    )
    if not global_path.exists():
        console.print(f"[red]Global config not found: {global_path}[/red]")
        return 1

    host = args.host or detect_host(global_path)

    all_keys = load_mcp_keys(global_path)
    # The user-global config (~/.config/opencode/opencode.json) can define
    # servers too (e.g. `seerr`) that aren't in the project config. Include
    # them so the profile can disable anything not selected.
    user_global = Path.home() / ".config" / "opencode"
    user_keys: dict[str, dict] = {}
    for candidate in (user_global / "opencode.json", user_global / "opencode.jsonc"):
        if candidate.exists():
            user_keys.update(load_mcp_keys(candidate))
    all_keys = {**user_keys, **all_keys}
    if not all_keys:
        console.print(f"[red]No 'mcp' block found in {global_path}[/red]")
        return 1

    console.print(f"[dim]Global: {global_path}  ·  host: {host}  ·  {len(all_keys)} servers[/dim]")
    console.print()

    available = list(all_keys)

    if args.non_interactive:
        for profile in PROFILES:
            if profile.name == args.non_interactive:
                label = profile.name
                enabled = [k for k in profile_keys(profile, host) if k in all_keys]
                break
        else:
            console.print(f"[red]Unknown profile '{args.non_interactive}'. "
                          f"Choices: {', '.join(p.name for p in PROFILES)}[/red]")
            return 1
    else:
        label, enabled = pick_profile(host, available)

    missing = [k for k in enabled if k not in all_keys]
    if missing:
        console.print(f"[yellow]Note: not present on this host, skipped: {', '.join(missing)}[/yellow]")

    config = build_config(all_keys, enabled)

    # Output dir
    if args.dir:
        out_dir = Path(args.dir)
    elif host == "proxmox":
        out_dir = Path(f"/root/{label}")
    else:
        base = Path.home() / "Documents" / "christopfarr"
        out_dir = base / label if label != "custom" else base / "custom"

    out_file = write_config(config, out_dir)

    enabled_list = "\n".join(f"  • {k}" for k in enabled) or "  (none)"
    console.print()
    console.print(f"[bold green]✓ Wrote {out_file}[/bold green]")
    console.print(f"[bold]Enabled ({len(enabled)}):[/bold]\n{enabled_list}")
    console.print(f"[dim]All other servers are set to enabled:false.[/dim]")
    console.print()
    console.print("[bold]This applies regardless of where you run opencode[/bold]")
    console.print("[dim](OPENCODE_CONFIG_CONTENT overrides the project config's MCP servers)[/dim]")
    console.print()
    console.print("[bold]Launch from anywhere:[/bold]  [cyan]opencode[/cyan]  (or run this wizard interactively and it launches for you)")
    console.print("[dim](quit and restart opencode if it is already running)[/dim]")

    console.print()
    if sys.stdin.isatty():
        import os
        import subprocess

        console.print("[cyan]opencode (with this MCP profile)...[/cyan]")
        subprocess.run(
            ["opencode"],
            env={**os.environ, "OPENCODE_CONFIG_CONTENT": json.dumps(config)},
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())