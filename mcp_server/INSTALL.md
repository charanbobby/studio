# Installing the Sri Studio Helper MCP server

## In Claude Code

Edit `~\.claude\mcp.json` (or per-project `.claude\mcp.json`):

```json
{
  "mcpServers": {
    "sri-studio-helper": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "D:/Python Applications/Sri Studio Helper",
        "python", "-m", "mcp_server"
      ],
      "env": {
        "HELPER_BASE_URL": "https://studio.sshub.dev",
        "HELPER_AUTH_KEY": "<paste from 1Password>"
      }
    }
  }
}
```

Restart Claude Code. The four tools (`helper_render_silent`, `helper_render_voice`, `helper_render_full`, `helper_skill`) appear in the tool list.

## Local-loopback testing

For testing against a Helper service running on localhost (no VPS required), set `HELPER_BASE_URL` to `http://127.0.0.1:8001`.
