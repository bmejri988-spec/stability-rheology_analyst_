import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command="python",
        args=["backend/mcpServer.py"]
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "rheology_assistant",
                {
                    "message": "What is the expected rheological behavior of a formulation with the following ingredients: 60.4% Aqua, 0.1% Disodium EDTA, 4.0% Glycerin, 15.0% Sodium Laureth Sulfate (70%), 10.0% Cocamidopropyl Betaine (30%), 5.0% Decyl Glucoside, 2.0% PEG-150 Distearate, 1.5% Citric Acid (10% sol.)?",
                    "history": [
                        {
                            "role": "user",
                            "text": "What is the expected rheological behavior of a formulation with the following ingredients: 60.4% Aqua, 0.1% Disodium EDTA, 4.0% Glycerin, 15.0% Sodium Laureth Sulfate (70%), 10.0% Cocamidopropyl Betaine (30%), 5.0% Decyl Glucoside, 2.0% PEG-150 Distearate, 1.5% Citric Acid (10% sol.)?"
                        }
                    ]
                }
            )

            print(result)

asyncio.run(main())