# Steps to build an MCP

Example for Radarr:
<service> = radarr
<repo> = Radarr/Radarr

1. `mkdir -p /home/savagecore/Git/arr-mcps/<service>-mcp/`
2. Open ghostty/terminal at `/home/savagecore/Git/arr-mcps/<service>-mcp/`
3. Send the prompt below to Plan agent in `opencode`:
```
Using /home/savagecore/Git/arr-mcps/tracearr-mcp as a base, let's plan an MCP server for <service> (https://github.com/<repo>) - you're in the repo folder /home/savagecore/Git/arr-mcps/<service>-mcp. Single initial commit at version 0.0.0. Ensure workflow action versions match tracearr (check they're the latest too). Full coverage of API read and writes.
```
4. Once the plan is ready, switch agent to `build-paid` and tell it to `go` to execute/proceed.
5. Once the build is complete, we prepare the GH repo and release the MCP via GitHub CI:
```
GHREPO=SavageCore/<service>-mcp \
  && { gh repo create "$GHREPO" --public --description "Model Context Protocol for <repo>" || true; } \
  && git remote add origin "https://github.com/$GHREPO.git" 2>/dev/null \
    || git remote set-url origin "https://github.com/$GHREPO.git" \
  && git branch -M main \
  && make bump-minor \
  && git add pyproject.toml uv.lock \
  && V=$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])') \
  && git commit -m "$V" \
  && git tag "v$V" \
  && git push -u origin main \
  && git push origin "v$V"
```
6. Close and reopen `opencode` for clean context. Switch to `build-paid` agent. Now tell the agent to self-register the MCP in the masterlist:

```
Add an entry for <service>-mcp to /home/savagecore/Git/arr-mcps/README.md under the appropriate category (add the heading if missing). Mirror the existing entries: H3 link to the repo, latest-release badge, one-line description, and install snippet with `uv tool install` and `claude mcp add`. Then commit and push the masterlist repo only (the per-MCP subfolder is gitignored - never add it):
```
```bash
cd /home/savagecore/Git/arr-mcps \
  && git add README.md \
  && git commit -m "feat: add radarr-mcp" \
  && git push
```

7. Close and reopen `opencode` for clean context. Switch to `build-paid` agent. Now tell the agent to install the MCP:

```
Add MCP https://github.com/SavageCore/<service>-mcp https://<service>.christopf-local.duckdns.org <apiKey> - use the IP from NPM in config not url. Update AGENTS.md with the new MCP entry.
```

7 happens both locally and on the server (192.168.50.3 root ssh via key /home/savagecore/.ssh/id_ed25519.pub)
