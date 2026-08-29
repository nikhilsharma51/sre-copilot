import asyncio
from mcp_client import mcp_session

async def main():
    async with mcp_session("github") as session:
        tools = await session.list_tools()
        for t in tools.tools:
            print(t.name)

asyncio.run(main())