Prompt
======

```
Using /home/savagecore/Git/arr-mcps/dashy-mcp as a base, let's plan a MCP server for <service> (https://github.com/<repo>/<service>) - you're in the repo folder /home/savagecore/Git/arr-mcps/<service>-mcp. Single initial commit at version 0.0.0. Ensure workflow action versions match dashy (check they're the latest too). Full coverage of API.
```

Once agent has built it, bump, tag and push to "release"

```bash
git remote add origin https://github.com/SavageCore/<service>-mcp.git \
  && git branch -M main \
  && make bump-minor \
  && git add -A \
  && V=$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])') \
  && git commit -m "$V" \
  && git tag "v$V" \
  && git push -u origin main \
  && git push origin "v$V"
```

Now tell the agent to self-register the MCP in the masterlist:

```
Add an entry for <service>-mcp to /home/savagecore/Git/arr-mcps/README.md under the appropriate category (add the heading if missing). Mirror the existing entries: H3 link to the repo, latest-release badge, one-line description, and install snippet with `uv tool install` and `claude mcp add`. Then commit and push the masterlist repo only (the per-MCP subfolder is gitignored - never add it):
```

```bash
cd /home/savagecore/Git/arr-mcps \
  && git add README.md \
  && git commit -m "feat: add <service>-mcp" \
  && git push
```

Now tell the agent to install the MCP:

```
Add MCP https://github.com/SavageCore/<service>-mcp https://<service>.christopf-local.duckdns.org <apiKey> - use the IP from NPM in config not url. Update AGENTS.md.
```