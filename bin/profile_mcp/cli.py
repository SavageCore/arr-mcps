"""Command-line interface for the profile-mcp wizard."""

import argparse
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from profile_mcp import __version__
from profile_mcp.profiles import (
    BUILTIN_NAMES,
    MODEL_SETS,
    PROFILES,
    load_custom_profiles,
    model_sets_for_host,
    profile_keys,
    save_custom_profile,
)

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
        "[dim]→ Pick a named profile (deploy / media / diagnostics / saved)[/dim]\n"
        "[dim]→ Build a custom set, or 'none' to load with no MCP servers[/dim]\n"
        "[dim]→ A <profile>/opencode.json is written; launch opencode there[/dim]"
    )
    console.print(Panel(info, border_style="cyan"))
    console.print()


def pick_set(sets: dict[str, dict[str, str]]) -> str:
    """Interactive model-set picker: ↑/↓ move · enter select · 1-9 jump · q quit.

    Returns the chosen model set name from `sets`. Quitting raises SystemExit
    without writing anything.
    """
    names = list(sets)
    if len(names) == 1:
        return names[0]
    cursor = 0
    console.clear()
    while True:
        console.print("[bold cyan]Choose a model set[/bold cyan]  [dim](↑/↓ move · enter select · 1-9 jump · q quit)[/dim]")
        console.print()

        for i, name in enumerate(names):
            highlight = i == cursor
            s = sets[name]
            line = Text()
            line.append(f"  {'▶' if highlight else ' '} ", style="bold cyan" if highlight else "dim")
            line.append(name, style="bold cyan" if highlight else "bold")
            line.append(f"  {s['desc']}", style="" if highlight else "dim")
            console.print(line)

        s = sets[names[cursor]]
        console.print()
        body = (
            f"  [bold]plan[/bold]   {s['plan']}\n"
            f"  [bold]build[/bold]  {s['build']}\n"
            f"  [bold]heavy[/bold]  {s['heavy']}"
        )
        console.print(
            Panel(
                body,
                title=f"[bold cyan]{names[cursor]}[/bold cyan] — {s['desc']}",
                border_style="cyan",
                expand=False,
            )
        )
        console.print()

        try:
            key = _read_key()
        except KeyboardInterrupt:
            raise SystemExit(130)
        console.clear()

        if key == "up":
            cursor = (cursor - 1) % len(names)
        elif key == "down":
            cursor = (cursor + 1) % len(names)
        elif key == "enter":
            return names[cursor]
        elif key in ("q", "Q", "esc"):
            console.print("[dim]Quit — nothing written.[/dim]")
            raise SystemExit(0)
        elif key in "123456789":
            idx = int(key) - 1
            if idx < len(names):
                cursor = idx


def pick_profile(host: str, available: list[str]) -> tuple[str, list[str]]:
    """Interactive profile picker: ↑/↓ move · enter select · n none · c custom · q quit.

    Returns (label, enabled_server_keys). 'label' is the profile name for
    built-in and saved profiles, 'custom' for a manual set, or 'none'.
    Quitting raises SystemExit without writing anything.
    """
    cursor = 0
    console.clear()
    while True:
        options = _profile_options(host, available)

        console.print("[bold cyan]Choose a profile[/bold cyan]  [dim](↑/↓ move · enter select · n none · c custom · q quit)[/dim]")
        console.print()

        for i, (name, tag, desc, keys) in enumerate(options):
            highlight = i == cursor
            marker = "▶" if highlight else " "
            line = Text()
            line.append(f"  {marker} ", style="bold cyan" if highlight else "dim")
            line.append(_display_name(name), style="bold cyan" if highlight else "bold")
            if tag:
                line.append(f" [{tag}]", style="magenta")
            line.append(f"  {desc}", style="" if highlight else "dim")
            if name not in ("custom", "none"):
                n = len(keys)
                line.append(f"  ({n} server{'s' if n != 1 else ''})", style="dim")
            console.print(line)

        name, _tag, _desc, keys = options[cursor]
        console.print()
        if name == "custom":
            title = "[bold cyan]Custom[/bold cyan] — manual set"
            body = "[dim]Select exactly the servers you want, then save or use them as-is.[/dim]"
        elif name == "none":
            title = "[bold cyan]None[/bold cyan] — no MCP servers"
            body = "[dim]Opens opencode with every MCP server disabled.[/dim]"
        elif not keys:
            title = f"[bold cyan]{_display_name(name)}[/bold cyan]"
            body = "[dim]None of this profile's servers are present on this host.[/dim]"
        else:
            title = f"[bold cyan]{_display_name(name)}[/bold cyan]"
            body = "\n".join(f"  [green]•[/green] {k}" for k in keys)
        console.print(Panel(body, title=title, border_style="cyan", expand=False))
        console.print()

        try:
            key = _read_key()
        except KeyboardInterrupt:
            raise SystemExit(130)
        console.clear()

        if key == "up":
            cursor = (cursor - 1) % len(options)
        elif key == "down":
            cursor = (cursor + 1) % len(options)
        elif key == "enter":
            name, _tag, _desc, keys = options[cursor]
            if name == "none":
                return "none", []
            if name == "custom":
                keys, edited = choose_custom(available)
                if keys is None:
                    continue  # backed out of the checklist — redraw the list
                return (edited or "custom"), keys
            return name, keys
        elif key in ("n", "N"):
            return "none", []
        elif key in ("c", "C"):
            keys, edited = choose_custom(available)
            if keys is None:
                continue  # backed out of the checklist — redraw the list
            return (edited or "custom"), keys
        elif key in ("q", "Q", "esc"):
            console.print("[dim]Quit — nothing written.[/dim]")
            raise SystemExit(0)
        elif key in "123456789":
            idx = int(key) - 1
            if idx < len(options):
                cursor = idx


def _display_name(name: str) -> str:
    """Capitalize only the first character, leaving the rest untouched."""
    return name[:1].upper() + name[1:]


def _profile_options(host: str, available: list[str]) -> list[tuple[str, str, str, list[str]]]:
    """Return (name, tag, description, enabled_keys) for every selectable option.

    Built-in profiles first, then saved custom profiles, then the custom and
    none actions. 'tag' is 'saved' for saved custom profiles, else ''.
    """
    options: list[tuple[str, str, str, list[str]]] = []
    for p in PROFILES:
        options.append(
            (p.name, "", p.description, [k for k in profile_keys(p, host) if k in available])
        )
    for name, keys in sorted(load_custom_profiles().items()):
        options.append(
            (name, "saved", "Saved custom profile", [k for k in keys if k in available])
        )
    options.append(("custom", "", "Pick exactly the servers you want", []))
    options.append(("none", "", "Load with no MCP servers at all", []))
    return options


def _read_key() -> str:
    """Read a single keypress in raw mode.

    Returns a normalized token: 'up'/'down'/'space'/'enter'/'esc', or the
    literal character for anything else.
    """
    import sys as _sys
    import termios
    import tty

    fd = _sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = _sys.stdin.read(1)
        if ch == "\x1b":
            seq = _sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            if seq == "[C":
                return "right"
            if seq == "[D":
                return "left"
            return "esc"
        if ch == " ":
            return "space"
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def choose_custom(available: list[str], edit_name: str | None = None) -> tuple[list[str] | None, str | None]:
    """Interactive checklist: ↑/↓ move · space toggle · e edit saved · s save · q back · enter done.

    Returns (selected_keys, edit_name). selected_keys is None when the user
    backs out (q) so the caller can return to the profile list.
    """
    header = "[bold]Available servers[/bold]  [dim](↑/↓ move · space toggle · e edit saved · s save · q back · enter done)[/dim]"
    selected: set[str] = set()
    cursor = 0
    if edit_name:
        selected = {k for k in load_custom_profiles().get(edit_name, []) if k in available}
    console.clear()
    while True:
        console.print(header)
        if edit_name:
            console.print(f"[dim]Editing profile: [bold cyan]{edit_name}[/bold cyan][/dim]")
            console.print()
        for i, key in enumerate(available):
            line = Text()
            line.append("  ")
            line.append("→" if i == cursor else " ",
                        style="bold cyan" if i == cursor else "dim")
            line.append(" ")
            line.append("[x]" if key in selected else "[ ]",
                        style="bold cyan" if i == cursor else "dim")
            line.append("  ")
            line.append(key, style="bold cyan" if i == cursor else "dim")
            console.print(line)
        console.print()
        console.print("[dim]↑/↓ move · space toggle · e edit saved · s save · q back · enter done[/dim]", end="\r")

        try:
            key = _read_key()
        except KeyboardInterrupt:
            raise SystemExit(130)
        console.clear()

        if key == "up":
            cursor = (cursor - 1) % len(available)
        elif key == "down":
            cursor = (cursor + 1) % len(available)
        elif key == "space":
            item = available[cursor]
            if item in selected:
                selected.discard(item)
            else:
                selected.add(item)
        elif key in ("e", "E"):
            target = _pick_saved_profile()
            if target:
                edit_name = target
                selected = {k for k in load_custom_profiles()[target] if k in available}
        elif key == "q":
            console.print("[dim]Back to profiles.[/dim]")
            return None, None
        elif key in ("s", "S"):
            if not selected:
                console.print("[yellow]Select at least one server before saving.[/yellow]")
            elif edit_name:
                save_custom_profile(edit_name, sorted(selected))
                console.print(f"[green]✓ Updated profile '{edit_name}'.[/green]")
            else:
                _save_selection(sorted(selected))
            time.sleep(0.9)
        elif key == "enter":
            break

    console.print()
    return sorted(selected), edit_name


def _pick_saved_profile() -> str | None:
    """Prompt for which saved profile to edit; returns its name or None."""
    saved = load_custom_profiles()
    if not saved:
        console.print("[yellow]No saved profiles yet — toggle some servers and press 's' to create one.[/yellow]")
        return None
    names = sorted(saved)
    console.print("[bold]Saved profiles:[/bold]")
    for i, name in enumerate(names, 1):
        servers = ", ".join(saved[name]) or "(none)"
        console.print(f"  [cyan]{i}[/cyan]  {name}  [dim]({servers})[/dim]")
    choice = Prompt.ask("[bold cyan]Edit which profile?[/bold cyan]", default="1").strip()
    try:
        return names[int(choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice.[/red]")
        return None


def _save_selection(keys: list[str]) -> None:
    """Prompt for a name and persist the current selection as a custom profile."""
    if not keys:
        console.print("[yellow]Select at least one server before saving.[/yellow]")
        return

    name = Prompt.ask("[bold cyan]Save selection as profile:[/bold cyan]").strip()
    if not name:
        console.print("[yellow]Not saved — name was empty.[/yellow]")
        return
    if name in BUILTIN_NAMES:
        console.print(f"[yellow]'{name}' is a built-in profile name; choose another.[/yellow]")
        return

    existing = load_custom_profiles()
    if name in existing:
        ok = Prompt.ask(
            f"[yellow]'{name}' already exists — overwrite?[/yellow]",
            choices=["y", "n"],
            default="n",
        ).strip().lower()
        if ok != "y":
            console.print("[dim]Save cancelled.[/dim]")
            return

    save_custom_profile(name, keys)
    console.print(f"[green]✓ Saved profile '{name}' — pick it from the profile list.[/green]")


def build_config(all_keys: dict[str, dict], enabled: list[str], set_name: str) -> dict:
    """Carry every server's full definition, toggling `enabled` on each.

    The definitions must be included inline (not just `enabled` flags): the
    profile is injected via OPENCODE_CONFIG_CONTENT, and when opencode runs
    outside the config's home directory the server definitions aren't loaded
    from any project config — so they must travel with the override.

    The agent block sets only `model` for plan/build/heavy, so they keep
    inheriting opencode's built-in modes and permissions for those names.
    """
    enabled_set = set(enabled)
    mcp = {}
    for key, server in all_keys.items():
        mcp[key] = {**server, "enabled": key in enabled_set}
    models = MODEL_SETS[set_name]
    agent = {role: {"model": models[role]} for role in ("plan", "build", "heavy")}
    return {"$schema": "https://opencode.ai/config.json", "mcp": mcp, "agent": agent}


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
                        help="Skip prompts; use a named profile (deploy|media|diagnostics|none|saved)")
    parser.add_argument("--set", choices=list(MODEL_SETS), default=None,
                        help="Model set for plan/build/heavy (free|go|deepseek); prompts if omitted")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.version:
        console.print(f"profile-mcp v{__version__}")
        return 0

    if args.help:
        console.print("profile-mcp - choose which MCP servers to load")
        console.print("  profile-mcp                       Interactive profile + model set picker")
        console.print("  profile-mcp --non-interactive deploy   Named profiles: deploy | media | diagnostics | none")
        console.print("  profile-mcp --set go              Model set: free | go | deepseek (per-host: proxmox is free only)")
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

    available = sorted(all_keys)

    host_sets = model_sets_for_host(host)
    default_set = next(iter(host_sets))
    if args.set and args.set not in host_sets:
        console.print(f"[yellow]'{args.set}' is not available on the {host} host — using '{default_set}'.[/yellow]")
    set_name = args.set if args.set in host_sets else (
        default_set if (args.non_interactive or len(host_sets) == 1) else pick_set(host_sets)
    )

    if args.non_interactive:
        non_int = args.non_interactive
        lower = non_int.lower()
        if lower == "none":
            label, enabled = "none", []
        elif lower in {k.lower() for k in load_custom_profiles()}:
            saved = next(k for k in load_custom_profiles() if k.lower() == lower)
            label = saved
            enabled = [k for k in load_custom_profiles()[saved] if k in all_keys]
        else:
            for profile in PROFILES:
                if profile.name == lower:
                    label = profile.name
                    enabled = [k for k in profile_keys(profile, host) if k in all_keys]
                    break
            else:
                console.print(f"[red]Unknown profile '{non_int}'. "
                              f"Choices: {', '.join(p.name for p in PROFILES)}, none, or a saved profile[/red]")
                return 1
    else:
        label, enabled = pick_profile(host, available)

    missing = [k for k in enabled if k not in all_keys]
    if missing:
        console.print(f"[yellow]Note: not present on this host, skipped: {', '.join(missing)}[/yellow]")

    config = build_config(all_keys, enabled, set_name)

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
    console.print(f"[bold]Model set:[/bold] {set_name}  ({MODEL_SETS[set_name]['desc']})")
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