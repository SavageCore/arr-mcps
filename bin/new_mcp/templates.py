"""Templates for plan prompts and README entries."""

PLAN_PROMPT = """Using /home/savagecore/Git/arr-mcps/tracearr-mcp as a base, let's plan an MCP server for {service} (https://github.com/{repo}) - you're in the repo folder /home/savagecore/Git/arr-mcps/{service}-mcp. Single initial commit at version 0.0.0. Ensure workflow action versions match tracearr (check they're the latest too). Full coverage of API read and writes."""

README_ENTRY = """### [{service}-mcp](https://github.com/SavageCore/{service}-mcp)
[![Latest release](https://img.shields.io/github/v/release/SavageCore/{service}-mcp)](https://github.com/SavageCore/{service}-mcp/releases/latest)

{description}

```bash
uv tool install {service}_mcp-*.whl
claude mcp add {service} --env {service_upper}_URL=... --env {service_upper}_API_KEY=... -- {service}-mcp
```
"""
