import json
import sys
import os
from contextlib import asynccontextmanager

from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args = ["-m", "mcp_server.server"],
)

SERVERS = {
    "ops": StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"]),
    "github": StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")},
    ),
    "slack": StdioServerParameters(
        command=os.environ.get("SLACK_MCP_COMMAND", "npx"),
        args=os.environ.get("SLACK_MCP_ARGS", "-y @slack/mcp-server").split(),
        env={"SLACK_BOT_TOKEN": os.environ.get("SLACK_BOT_TOKEN", "")},
    ),
}

@asynccontextmanager
async def mcp_session(server : str ="ops"):
     params = SERVERS.get(server)
     if params is None:
         raise ValueError(f"Unknown MCP server: {server!r}. Valid options: {list(SERVERS)}")
     async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

def _extract(result) ->object:
    if result.isError:
        raise RuntimeError(f"MCP tool call failed: {result.content}")
    texts = [c.text for c in result.content if isinstance(c, TextContent)]
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except json.JSONDecodeError:
            return texts[0]
    return texts

async def call_mcp_tool(name: str, arguments: dict, server: str = "ops") -> object:
    async with mcp_session(server) as session:
        result = await session.call_tool(name, arguments)
        return _extract(result)