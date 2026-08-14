"""Command-line interface for new-mcp wizard."""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from profile_mcp.cli import pick_set
from profile_mcp.profiles import PAID_MODEL_SETS, paid_model_sets

from new_mcp import __version__
from .steps import (
    parse_github_url,
    scaffold_dir,
    plan_and_build,
    release_to_github,
    register_in_readme,
    install_locally,
    install_remotely,
    set_log_file,
    resolve_instance_url,
)


def _find_repo_root() -> Path:
    """Resolve the arr-mcps checkout, whether run from source or as a uv tool.

    When run from the source checkout, __file__ is <repo>/bin/new_mcp/cli.py so
    parent.parent.parent is the repo. When installed via `uv tool install`,
    __file__ lives under ~/.local/share/uv/tools/new-mcp/... which is useless,
    so fall back to an env override, then the default checkout location.
    """
    env = os.environ.get("ARR_MCPS_REPO")
    if env:
        return Path(env).expanduser().resolve()

    from_source = Path(__file__).resolve().parent.parent.parent
    if (from_source / "bin" / "new_mcp").exists():
        return from_source

    default = Path.home() / "Git" / "arr-mcps"
    if default.exists():
        return default

    raise RuntimeError(
        "Could not locate the arr-mcps checkout. Set ARR_MCPS_REPO to its path."
    )


REPO_ROOT = _find_repo_root()
LOG_DIR = Path.home() / ".local" / "share" / "mcpsmith" / "logs"


def create_console_with_log():
    """Create a console that records output for logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"mcpsmith_{timestamp}.log"
    return Console(record=True), log_file


console, log_file = create_console_with_log()


def save_log():
    """Save recorded console output to file."""
    try:
        with open(log_file, "w") as f:
            f.write(console.export_text())
    except Exception as e:
        console.print(f"[yellow]Warning: Could not save log file: {e}[/yellow]")


def open_repo(gh_url: str, local_dir: Path, app: str = "browser"):
    """Open GitHub repo in browser or GitKraken.

    Args:
        gh_url: Full GitHub URL (https://github.com/owner/repo)
        local_dir: Local checkout directory (used by GitKraken)
        app: 'browser' or 'gitkraken'
    """
    if app == "gitkraken":
        # GitKraken opens the local checkout directory directly,
        # like `gitkraken --path <dir>` (not the gitkraken:// URL scheme)
        subprocess.run(["gitkraken", "--path", str(local_dir)], capture_output=True)
    else:
        subprocess.run(["xdg-open", gh_url], capture_output=True)


def print_header():
    """Print welcome header with branding and explanation."""
    header = Text()
    header.append("⚙️  ", style="bold cyan")
    header.append("MCPsmith", style="bold cyan")
    header.append(" — Craft new MCP servers", style="dim cyan")

    console.print()
    console.print(header)
    console.print()

    info = (
        "Scaffolds, builds, and releases new Model Context Protocol servers "
        "for the arr ecosystem (Sonarr, Radarr, Lidarr, etc.)\n\n"
        "[dim]→ Paste a GitHub repo URL (e.g., https://github.com/Sonarr/Sonarr)[/dim]\n"
        "[dim]→ The wizard will plan the MCP design (via opencode)[/dim]\n"
        "[dim]→ Build the code, release to GitHub, and install locally/remotely[/dim]"
    )

    console.print(Panel(info, border_style="cyan"))
    console.print()


def main():
    parser = argparse.ArgumentParser(
        prog="MCPsmith",
        description="Craft new Model Context Protocol servers",
        epilog="Example: new-mcp https://github.com/Sonarr/Sonarr",
        add_help=False
    )
    parser.add_argument("urls", nargs="*", help="GitHub repo URLs")
    parser.add_argument("--skip-remote", action="store_true", help="Skip remote deploy")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve plan and build")
    parser.add_argument("--provider", choices=list(PAID_MODEL_SETS), default=None,
                        help="Model set for plan/build stages (go, go-cheap, deepseek, deepseek-cheap). Skips the prompt.")
    parser.add_argument("--url", default=None,
                        help="Override the instance URL used for opencode registration (skips NPM resolution).")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.help:
        print_header()
        console.print("[bold]Usage:[/bold]")
        console.print("  new-mcp <url> [<url> ...]              Process one or more repos")
        console.print("  new-mcp                                 Interactive mode")
        console.print("  new-mcp --skip-remote <url>             Skip remote deploy")
        console.print("  new-mcp --auto-approve                  Batch mode (auto-approve plans)")
        console.print("  new-mcp --provider go                   Model set for plan/build (skips prompt; choices: go, go-cheap, deepseek, deepseek-cheap)")
        console.print("  new-mcp --url <instance-url>            Override registration URL (skips NPM resolution)")
        console.print("  new-mcp --version                       Show version")
        return 0

    if args.version:
        console.print(f"MCPsmith v{__version__}")
        console.print("https://github.com/SavageCore/arr-mcps/tree/main/bin")
        return 0

    # Set up logging
    set_log_file(log_file)

    print_header()

    urls = args.urls or []

    # Interactive URL entry if none provided
    if not urls:
        console.print("[bold]Enter GitHub repo URLs[/bold]")
        console.print()
        url = Prompt.ask("[cyan]Repo URL[/cyan]", default="", show_default=False).strip()
        if url:
            urls.append(url)
            while True:
                url = Prompt.ask("[cyan]Add another? (blank to start)[/cyan]", default="", show_default=False).strip()
                if not url:
                    break
                urls.append(url)

    if not urls:
        console.print("[yellow]No URLs provided.[/yellow]")
        return 1

    console.print()
    console.print(f"[bold cyan]Processing {len(urls)} repo(s)[/bold cyan]")
    console.print()

    # Model set for the opencode plan/build stages (asked once, or via --provider)
    model_set = args.provider
    if not model_set:
        model_set = pick_set(paid_model_sets(), title="Which provider should plan/build use?")
        console.print()

    # Collect API credentials upfront (instance URLs are auto-resolved per service)
    console.print("[bold]API Credentials[/bold]")
    console.print("[dim](instance URLs resolved via nginx proxy manager)[/dim]")
    console.print()

    from getpass import getpass
    console.print("[cyan]API Key or Auth Token (for opencode registration)[/cyan]:")
    auth_token = getpass().strip()
    console.print()

    # Ask about auto-approve for batch runs
    auto_approve = args.auto_approve
    if not auto_approve and len(urls) > 1:
        auto_approve = Confirm.ask(
            "[bold]Auto-approve plan and proceed to build? (batch mode, no notifications)[/bold]",
            default=False
        )

    # Interactive plan/build (model can ask questions) only when a human is
    # attached and we're not in batch auto-approve mode.
    interactive = not auto_approve and sys.stdin.isatty()

    console.print()

    failed = []
    completed = []  # Track successful repos
    for i, url in enumerate(urls, 1):
        console.print(f"[bold cyan][{i}/{len(urls)}][/bold cyan] [bold]{url}[/bold]")
        console.print()

        try:
            repo, service = parse_github_url(url)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")
            failed.append((url, str(e)))
            console.print()
            continue

        mcp_dir = REPO_ROOT / f"{service}-mcp"

        # Warn if already exists
        if mcp_dir.exists():
            console.print(f"[yellow]⚠ {mcp_dir} already exists[/yellow]")
            console.print("[dim]Resuming from plan/build stage...[/dim]")
            console.print()
        else:
            mcp_dir = scaffold_dir(service, REPO_ROOT)
            console.print(f"[green]✓ Scaffolded {service}-mcp[/green]")
            console.print()

        # Plan & build
        if not plan_and_build(service, repo, mcp_dir, auto_approve=auto_approve, model_set=model_set, interactive=interactive):
            failed.append((url, "plan/build cancelled or failed"))
            console.print()
            continue

        # Release
        if not release_to_github(service, repo, mcp_dir):
            failed.append((url, "github release failed"))
            console.print()
            continue

        # README
        if not register_in_readme(service, mcp_dir, REPO_ROOT, model_set=model_set):
            console.print("[yellow]WARNING: README registration had issues, but continuing...[/yellow]")
            console.print()

        # Resolve instance URL if auth token provided (or use --url override)
        instance_url = args.url or ""
        if not instance_url and auth_token:
            console.print()
            console.print("[dim]Resolving instance URL via nginx proxy manager...[/dim]")
            instance_url = resolve_instance_url(service, model_set=model_set)
            if instance_url:
                console.print(f"[green]✓ Resolved to {instance_url}[/green]")
                # Allow override for custom instances (e.g., Tailscale)
                console.print(f"[dim]Leave blank to use {instance_url}[/dim]")
                override = Prompt.ask(
                    "[cyan]Override URL?[/cyan]",
                    default=""
                ).strip()
                if override:
                    instance_url = override
            else:
                console.print(f"[yellow]⚠ Could not resolve {service}.christopf-local.duckdns.org[/yellow]")
                instance_url = Prompt.ask("[cyan]Enter instance URL[/cyan]", default="").strip()
            console.print()

        # Local install & opencode registration
        if not install_locally(service, mcp_dir, instance_url, auth_token):
            console.print("[yellow]WARNING: Local install had issues, but continuing...[/yellow]")
            console.print()

        # Remote deploy & opencode registration
        if not args.skip_remote:
            if not install_remotely(service, repo, instance_url, auth_token):
                console.print("[yellow]WARNING: Remote deploy had issues[/yellow]")
                console.print()

        console.print("[green bold]✓ Complete![/green bold]")
        completed.append((service, repo))
        console.print()

    # Summary and cleanup
    console.print()
    if failed:
        console.print("[bold red]Failed:[/bold red]")
        for url, reason in failed:
            console.print(f"  {url}: {reason}")
        exit_code = 1
    else:
        console.print("[bold green]All done![/bold green]")
        exit_code = 0

    # Save log and show path
    console.print()
    save_log()
    console.print(f"[dim]Log saved: {log_file}[/dim]")

    # Offer to open GitHub repos
    if completed:
        console.print()
        if len(completed) == 1:
            service, repo = completed[0]
            gh_url = f"https://github.com/SavageCore/{service}-mcp"
            mcp_dir = REPO_ROOT / f"{service}-mcp"
            console.print(f"[dim]{gh_url}[/dim]")
            choice = Prompt.ask(
                "[bold]Open repo?[/bold]",
                choices=["browser", "gitkraken", "both", "no"],
                default="gitkraken"
            )
            if choice == "both":
                open_repo(gh_url, mcp_dir, "browser")
                open_repo(gh_url, mcp_dir, "gitkraken")
            elif choice != "no":
                open_repo(gh_url, mcp_dir, choice)
        else:
            console.print("[bold]Completed repos:[/bold]")
            for service, repo in completed:
                console.print(f"  • https://github.com/SavageCore/{service}-mcp")
            choice = Prompt.ask(
                "[bold]Open all in?[/bold]",
                choices=["browser", "gitkraken", "both", "no"],
                default="gitkraken"
            )
            if choice == "both":
                for service, repo in completed:
                    gh_url = f"https://github.com/SavageCore/{service}-mcp"
                    mcp_dir = REPO_ROOT / f"{service}-mcp"
                    open_repo(gh_url, mcp_dir, "browser")
                    open_repo(gh_url, mcp_dir, "gitkraken")
            elif choice != "no":
                for service, repo in completed:
                    gh_url = f"https://github.com/SavageCore/{service}-mcp"
                    mcp_dir = REPO_ROOT / f"{service}-mcp"
                    open_repo(gh_url, mcp_dir, choice)

    # Keep terminal open for review
    console.print()
    Prompt.ask("[dim]Press Enter to close[/dim]")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
