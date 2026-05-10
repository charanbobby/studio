"""MCP server registration. Maps four tools to mcp_server.tools."""
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from . import tools

server = Server("sri-studio-helper")

@server.list_tools()
async def _list_tools() -> list[Tool]:
    return [
        Tool(name="helper_render_silent",
             description="Render the silent preview of a Helper screencast. "
                         "Submit a project_dir; returns preview_url + estimate_usd. "
                         "Pause for human review of the preview before calling helper_render_voice.",
             inputSchema={"type": "object",
                          "properties": {"project_dir": {"type": "string"}},
                          "required": ["project_dir"]}),
        Tool(name="helper_render_voice",
             description="Approve a silent preview and render the voiced final. "
                         "Costs ElevenLabs tokens; check estimate_usd from helper_render_silent first.",
             inputSchema={"type": "object",
                          "properties": {"job_id": {"type": "string"}},
                          "required": ["job_id"]}),
        Tool(name="helper_render_full",
             description="Render silent + voice in one call (skips review gate). "
                         "ONLY use when the project is a known-good template; otherwise prefer helper_render_silent.",
             inputSchema={"type": "object",
                          "properties": {"project_dir": {"type": "string"}},
                          "required": ["project_dir"]}),
        Tool(name="helper_skill",
             description="Fetch the Sri Studio Helper SKILL.md (silent-first lessons, beat structure, "
                         "scene authoring, anti-patterns). Call this once at session start to load "
                         "best-practices guidance before constructing a project.",
             inputSchema={"type": "object", "properties": {}}),
    ]

@server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
    fn = {
        "helper_render_silent": tools.helper_render_silent,
        "helper_render_voice":  tools.helper_render_voice,
        "helper_render_full":   tools.helper_render_full,
        "helper_skill":         tools.helper_skill,
    }[name]
    result = fn(arguments)
    payload = result if isinstance(result, str) else json.dumps(result)
    return [TextContent(type="text", text=payload)]

async def serve() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())
