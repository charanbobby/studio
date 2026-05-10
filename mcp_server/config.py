"""Env config for the MCP server. Exits 1 with stderr message if missing."""
import os, sys

def _required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"[mcp_server] missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return v

def base_url() -> str:
    return os.environ.get("HELPER_BASE_URL", "https://studio.sshub.dev").rstrip("/")

def auth_key() -> str:
    return _required("HELPER_AUTH_KEY")
