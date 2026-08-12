"""Individual step implementations for the new-MCP workflow."""

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse

import rich.console
import rich.progress
from rich.prompt import Confirm, Prompt

from .templates import PLAN_PROMPT, README_ENTRY


console = rich.console.Console()

# Log file handle (will be set by cli.py)
_log_file_handle = None


def set_log_file(file_path: Path):
    """Set log file for recording output."""
    global _log_file_handle
    try:
        _log_file_handle = open(file_path, "a")
        _log_file_handle.write(f"\n=== MCPsmith session started ===\n\n")
    except:
        pass


def resolve_instance_url(service: str) -> str:
    """Query opencode agent to resolve duckdns URL to IP:port via nginx proxy manager.

    Uses the opencode agent in ~/Documents/christopfarr/ to query NPM for the
    actual IP:port that {service}.christopf-local.duckdns.org maps to.

    Returns the IP:port, or empty string if resolution fails.
    """
    duckdns_url = f"https://{service}.christopf-local.duckdns.org"

    prompt = (
        f"What is the IP and port for {duckdns_url} in Nginx Proxy Manager? "
        f"Just respond with 'IP:PORT' (e.g., 192.168.1.100:5000), nothing else."
    )

    result = subprocess.run(
        ["opencode", "run", "--dir", str(Path.home() / "Documents/christopfarr"),
         prompt],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        return ""

    # Parse response to extract IP:PORT
    for line in result.stdout.split("\n"):
        line = line.strip()
        # Look for pattern IP:PORT
        if ":" in line and any(c.isdigit() for c in line.split(":")[0]):
            return line
        # Also accept just IP if that's all we get
        if all(c.isdigit() or c == "." for c in line.split(":")[0]):
            return line

    return ""


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL into (repo, service).

    url: https://github.com/Sonarr/Sonarr or git@github.com:Sonarr/Sonarr.git
    returns: ('Sonarr/Sonarr', 'sonarr')
    """
    url = url.strip()
    if url.endswith('.git'):
        url = url[:-4]

    # Extract owner/repo from various formats
    if 'github.com/' in url:
        parts = url.split('github.com/')[-1].split('/')
    elif '@github.com:' in url:
        parts = url.split('@github.com:')[-1].split('/')
    else:
        raise ValueError(f"Not a GitHub URL: {url}")

    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL format: {url}")

    repo = f"{parts[0]}/{parts[1]}"
    service = parts[1].lower()
    return repo, service


def scaffold_dir(service: str, repo_path: Path) -> Path:
    """Create <service>-mcp directory."""
    mcp_dir = repo_path / f"{service}-mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    return mcp_dir


def plan_and_build(service: str, repo: str, mcp_dir: Path, auto_approve: bool = False) -> bool:
    """Run opencode plan then build stages. Returns True if build succeeds.

    Args:
        service: Service name (e.g., 'sonarr')
        repo: GitHub repo (e.g., 'Sonarr/Sonarr')
        mcp_dir: Working directory
        auto_approve: If True, skip confirmation and proceed to build
    """
    console.print()
    console.print(f"[bold cyan]Step 3-4: Plan & Build ({service}-mcp)[/bold cyan]")
    console.print()

    plan_prompt = PLAN_PROMPT.format(service=service, repo=repo)

    console.print("[dim]Launching opencode plan agent... (output below)[/dim]")
    console.print()

    # Run plan in foreground so user sees opencode's formatted output
    result = subprocess.run(
        ["opencode", "run", "--dir", str(mcp_dir), "--agent", "plan",
         "--title", f"{service}-mcp plan", plan_prompt],
        cwd=str(mcp_dir)
    )

    if result.returncode != 0:
        console.print("[red]Plan failed.[/red]")
        return False

    console.print()

    if auto_approve:
        console.print("[green]✓ Auto-approved (batch mode)[/green]")
        console.print()
    else:
        confirm = Confirm.ask(
            "[bold]Plan ready above — continue to build-paid (paid run)?[/bold]",
            default=True
        )

        if not confirm:
            console.print("[yellow]Skipping build. Directory left in place for retry.[/yellow]")
            return False

        console.print()

    console.print("[dim]Launching opencode build-paid agent... (output below)[/dim]")
    console.print()

    result = subprocess.run(
        ["opencode", "run", "--dir", str(mcp_dir), "--agent", "build-paid",
         "--continue", "go"],
        cwd=str(mcp_dir)
    )

    if result.returncode != 0:
        console.print("[red]Build failed.[/red]")
        return False

    console.print()
    console.print("[green]✓ Build complete[/green]")
    return True


def release_to_github(service: str, repo: str, mcp_dir: Path) -> bool:
    """Release new MCP to GitHub: create repo, bump version, tag, push."""
    console.print()
    console.print(f"[bold cyan]Step 5: Release to GitHub[/bold cyan]")
    console.print()

    gh_repo = f"SavageCore/{service}-mcp"

    with console.status("[bold]Creating GitHub repo and releasing...[/bold]"):
        # Create repo (idempotent via || true)
        subprocess.run(
            ["gh", "repo", "create", gh_repo, "--public",
             "--description", f"Model Context Protocol for {repo}",
             "--homepage", "https://github.com/SavageCore/arr-mcps"],
            cwd=str(mcp_dir),
            capture_output=True
        )

        # Ensure remote origin
        subprocess.run(
            ["git", "remote", "add", "origin", f"https://github.com/{gh_repo}.git"],
            cwd=str(mcp_dir),
            capture_output=True
        )
        subprocess.run(
            ["git", "remote", "set-url", "origin", f"https://github.com/{gh_repo}.git"],
            cwd=str(mcp_dir),
            capture_output=True
        )

        # Ensure main branch
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=str(mcp_dir),
            capture_output=True
        )

        # Bump minor version
        result = subprocess.run(
            ["make", "bump-minor"],
            cwd=str(mcp_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]make bump-minor failed: {result.stderr}[/red]")
            return False

        # Read version from pyproject.toml
        pyproject = mcp_dir / "pyproject.toml"
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                version = data["project"]["version"]
        except Exception as e:
            console.print(f"[red]Failed to read version: {e}[/red]")
            return False

        # Commit and tag
        subprocess.run(
            ["git", "add", "pyproject.toml", "uv.lock"],
            cwd=str(mcp_dir),
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", version],
            cwd=str(mcp_dir),
            capture_output=True
        )
        subprocess.run(
            ["git", "tag", f"v{version}"],
            cwd=str(mcp_dir),
            capture_output=True
        )

        # Push
        result = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=str(mcp_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]git push main failed: {result.stderr}[/red]")
            return False

        result = subprocess.run(
            ["git", "push", "origin", f"v{version}"],
            cwd=str(mcp_dir),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]git push tag failed: {result.stderr}[/red]")
            return False

    console.print(f"[green]✓ Released {version} to {gh_repo}[/green]")
    return True


def register_in_readme(service: str, mcp_dir: Path, repo_path: Path) -> bool:
    """Register the new MCP in README.md."""
    console.print()
    console.print(f"[bold cyan]Step 6: Register in README.md[/bold cyan]")
    console.print()

    readme = repo_path / "README.md"

    try:
        with open(readme) as f:
            content = f.read()
    except Exception as e:
        console.print(f"[red]Failed to read README: {e}[/red]")
        return False

    # Find all H2 headings (categories)
    headings = re.findall(r"^## (.+)$", content, re.MULTILINE)
    if not headings:
        console.print("[red]No ## headings found in README.[/red]")
        return False

    # Use opencode to pick the best category
    console.print()
    console.print("[dim]Determining best README category...[/dim]")

    categories_list = ", ".join(h for h in headings if h not in ["Adding a new MCP", "License"])
    prompt = (
        f"Which README category best fits {service}-mcp? "
        f"Options: {categories_list}. "
        f"Just respond with the category name, nothing else."
    )

    result = subprocess.run(
        ["opencode", "run", "--dir", str(mcp_dir), prompt],
        capture_output=True,
        text=True,
        timeout=30
    )

    category = None
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and line in headings:
                category = line
                break

    # Fall back to user prompt if AI couldn't determine
    if not category:
        console.print("[yellow]⚠ Could not auto-determine category[/yellow]")
        console.print("Existing categories:")
        for i, heading in enumerate(headings, 1):
            console.print(f"  {i}. {heading}")
        console.print(f"  {len(headings) + 1}. [New category]")

        choice = Prompt.ask(
            "Pick a category (number) or type a new name",
            choices=[str(i) for i in range(1, len(headings) + 2)]
        )

        if choice == str(len(headings) + 1):
            category = Prompt.ask("New category name")
        else:
            category = headings[int(choice) - 1]
    else:
        console.print(f"[green]✓ Category: {category}[/green]")

    # Generate description via opencode
    console.print()
    console.print("[dim]Generating README description...[/dim]")

    prompt = (
        f"Write a single-line description (max 80 chars) for the {service}-mcp README entry. "
        f"Describe what this MCP does in one concise sentence for a technical audience. "
        f"Just the description, nothing else."
    )

    result = subprocess.run(
        ["opencode", "run", "--dir", str(mcp_dir), prompt],
        capture_output=True,
        text=True,
        timeout=30
    )

    description = None
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and len(line) < 100:  # Sanity check
                description = line
                break

    # Fall back to README excerpt if AI generation fails
    if not description:
        new_readme = mcp_dir / "README.md"
        if new_readme.exists():
            try:
                with open(new_readme) as f:
                    lines = f.readlines()
                    for line in lines[1:]:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            description = line.rstrip(".")
                            break
            except:
                pass

    # Show description and allow override
    if description:
        console.print(f"[green]✓ Generated: {description}[/green]")
    else:
        console.print("[yellow]⚠ Could not generate description[/yellow]")
        description = Prompt.ask("One-line description", default="")
        if not description:
            return False

    # Render entry
    service_upper = service.upper()
    entry = README_ENTRY.format(
        service=service,
        service_upper=service_upper,
        description=description
    )

    # Find insertion point: end of the chosen ## category
    category_pattern = f"^## {re.escape(category)}$"
    match = re.search(category_pattern, content, re.MULTILINE)
    if not match:
        console.print(f"[red]Category '{category}' not found in README.[/red]")
        return False

    insert_pos = match.end()

    # Find next ## or end of file
    next_heading = re.search(r"\n## ", content[insert_pos:])
    if next_heading:
        insert_pos += next_heading.start()
    else:
        insert_pos = len(content)

    # Find the last entry before this position, sort alphabetically
    section_content = content[match.end():insert_pos]
    existing_entries = re.findall(r"^### \[([^\]]+)", section_content, re.MULTILINE)

    # Find insertion point alphabetically
    entry_name = f"{service}-mcp"
    insert_before_entry = None
    for existing in sorted(existing_entries):
        if existing.lower() > entry_name.lower():
            insert_before_entry = existing
            break

    if insert_before_entry:
        # Insert before this entry
        pattern = f"^### \\[{re.escape(insert_before_entry)}\\]"
        match = re.search(pattern, content[match.end():], re.MULTILINE)
        if match:
            insert_pos = match.end() - len(match.group()) + match.start() + match.end()

    # Simple approach: append after category heading with blank line
    split_pos = match.end()
    new_content = content[:split_pos] + "\n" + entry + "\n" + content[split_pos:]

    # Dedup: remove the old entry if present (to handle re-runs)
    new_content = re.sub(
        f"^### \\[{service}-mcp\\].*?(?=^###|^##|\\Z)",
        "",
        new_content,
        flags=re.MULTILINE | re.DOTALL
    )

    # Re-insert after category, deduplicated, sorted alphabetically
    match = re.search(f"^## {re.escape(category)}$", new_content, re.MULTILINE)
    if match:
        split_pos = match.end()
        section_start = split_pos

        # Find the end of this category's section (next ## or EOF)
        next_heading = re.search(r"\n## ", new_content[split_pos:])
        if next_heading:
            section_end = split_pos + next_heading.start() + 1
        else:
            section_end = len(new_content)

        section_text = new_content[section_start:section_end]

        # Split section into entry blocks (from each ### [ up to next ### [, ##, or end)
        entry_blocks = re.split(r"(?=\n### \[)", section_text)
        # First block is leading whitespace/blank lines before the first entry
        leading_ws = entry_blocks[0]

        # Remaining blocks are actual entries
        entries = entry_blocks[1:] if len(entry_blocks) > 1 else []

        if entries:
            # Sort entries by name (extracted from ### [name]...)
            def extract_name(block):
                match = re.search(r"^### \[([^\]]+)\]", block)
                return match.group(1).lower() if match else ""

            entries_sorted = sorted(entries, key=extract_name)

            # Rebuild section
            new_section = leading_ws + "".join(entries_sorted)
            new_content = new_content[:section_start] + new_section + new_content[section_end:]

    try:
        with open(readme, "w") as f:
            f.write(new_content)
    except Exception as e:
        console.print(f"[red]Failed to write README: {e}[/red]")
        return False

    # Commit in root repo
    with console.status("[bold]Committing to masterlist...[/bold]"):
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=str(repo_path),
            capture_output=True
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"feat: add {service}-mcp"],
            cwd=str(repo_path),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[yellow]Commit skipped (no changes or error): {result.stderr}[/yellow]")
        else:
            subprocess.run(
                ["git", "push"],
                cwd=str(repo_path),
                capture_output=True
            )

    console.print(f"[green]✓ Registered {service}-mcp in README[/green]")
    return True


def install_locally(service: str, mcp_dir: Path, instance_url: str = "", auth_token: str = "") -> bool:
    """Install the new MCP locally and register with opencode if credentials provided."""
    console.print()
    console.print(f"[bold cyan]Step 7a: Install locally[/bold cyan]")
    console.print()

    with console.status("[bold]Installing with uv tool install...[/bold]"):
        result = subprocess.run(
            ["uv", "tool", "install", "--force", str(mcp_dir)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]Installation failed: {result.stderr}[/red]")
            return False

    console.print(f"[green]✓ Installed {service}-mcp locally[/green]")

    # Register with opencode if credentials provided
    if instance_url and auth_token:
        console.print()
        console.print("[dim]Registering with opencode...[/dim]")

        service_upper = service.upper()
        with console.status(f"[bold]Adding {service}-mcp to opencode...[/bold]"):
            result = subprocess.run(
                ["opencode", "mcp", "add", service,
                 f"--env", f"{service_upper}_URL={instance_url}",
                 f"--env", f"{service_upper}_API_KEY={auth_token}",
                 "--", f"{service}-mcp"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                console.print(f"[yellow]⚠ opencode registration had issues: {result.stderr}[/yellow]")
                return False

        console.print(f"[green]✓ Registered {service}-mcp with opencode[/green]")
    else:
        console.print()
        console.print("[dim]Skipped registration (no credentials provided)[/dim]")

    return True


def install_remotely(service: str, repo: str, instance_url: str = "", auth_token: str = "") -> bool:
    """Deploy to remote Proxmox host and register with opencode."""
    console.print()
    console.print(f"[bold cyan]Step 7b: Deploy to 192.168.50.3[/bold cyan]")
    console.print()

    host = "192.168.50.3"
    key_path = Path.home() / ".ssh" / "id_ed25519"

    if not key_path.exists():
        console.print(f"[yellow]SSH key not found at {key_path}, skipping remote deploy[/yellow]")
        return False

    gh_repo = f"SavageCore/{service}-mcp"
    remote_dir = f"/root/{service}-mcp"

    with console.status(f"[bold]Deploying to {host}:{remote_dir}...[/bold]"):
        cmd = (
            f"cd /root && "
            f"git clone https://github.com/{gh_repo}.git {service}-mcp 2>/dev/null || "
            f"(cd {remote_dir} && git fetch origin && git reset --hard origin/main) && "
            f"cd {remote_dir} && uv tool install --force ."
        )

        result = subprocess.run(
            ["ssh", f"root@{host}", "--", cmd],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            console.print(f"[red]Remote deploy failed:\n{result.stderr}[/red]")
            return False

    console.print(f"[green]✓ Deployed {service}-mcp to {host}[/green]")

    # Register with opencode on remote if credentials provided
    if instance_url and auth_token:
        console.print()
        console.print("[dim]Registering with opencode on remote host...[/dim]")

        service_upper = service.upper()
        cmd = (
            f"opencode mcp add {service} "
            f"--env {service_upper}_URL={instance_url} "
            f"--env {service_upper}_API_KEY={auth_token} "
            f"-- {service}-mcp"
        )

        result = subprocess.run(
            ["ssh", f"root@{host}", "--", cmd],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            console.print(f"[yellow]⚠ Remote opencode registration had issues[/yellow]")
            # Don't fail the whole deploy, show instructions instead
        else:
            console.print(f"[green]✓ Registered {service}-mcp on {host} opencode[/green]")

    return True
