import json
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args = ["-m", "mcp_server.server"],
)

@asynccontextmanager
async def mcp_session():
     async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

def _extract(result) ->object:
    if result.is_error:
        raise RuntimeError(f"MCP tool call failed: {result.content}")
    texts = [c.text for c in result.content if isinstance(c, TextContent)]
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except json.JSONDecodeError:
            return texts[0]
    return texts

async def call_mcp_tool(name: str, arguments: dict) -> object:
    async with mcp_session() as session:
        result = await session.call_tool(name, arguments)
        return _extract(result)