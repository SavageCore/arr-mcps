"""Templates for plan prompts and README entries."""

PLAN_PROMPT = """Using /home/savagecore/Git/arr-mcps/tracearr-mcp as a base, let's plan an MCP server for {service} (https://github.com/{repo}) - you're in the repo folder /home/savagecore/Git/arr-mcps/{service}-mcp. Single initial commit at version 0.0.0. Ensure workflow action versions match tracearr (check they're the latest too). Full coverage of API read and writes, BUT expose it as ~5-15 resource-scoped portmanteau tools, not one MCP tool per REST endpoint - see /home/savagecore/Git/arr-mcps/AGENTS.md's "Tool design standard" section for the exact pattern (an `operation`-enum dispatcher per resource group, e.g. {service}_queue/{service}_config, with per-endpoint functions kept as plain callables looked up by name). Do not register a tool per endpoint even if the API is small; only tracearr itself is exempt, and only because it predates this standard and already sits under the ceiling. A larger API (dozens to hundreds of endpoints) needs the grouped pattern from the very first commit, not a follow-up refactor."""

README_ENTRY = """### [{service}-mcp](https://github.com/{owner}/{service}-mcp)
[![Latest release](https://img.shields.io/github/v/release/{owner}/{service}-mcp)](https://github.com/{owner}/{service}-mcp/releases/latest)

{description}

```bash
uv tool install {service}_mcp-*.whl
claude mcp add {service} --env {service_upper}_URL=... --env {service_upper}_API_KEY=... -- {service}-mcp
```
"""
