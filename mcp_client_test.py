import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command="python",
        args=["backend/mcpServer.py"],  # adjust path
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("TOOLS:")
            for tool in tools.tools:
                print("-", tool.name)

            result = await session.call_tool(
                "health",
                {}
            )

            print(result)


asyncio.run(main())