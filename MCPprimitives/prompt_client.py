import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["prompt_server.py"]
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()
            print("Available prompts:")
            for p in prompts.prompts:
                print("-", p.name)

            # Fetch a greeting prompt
            print("\nFetching greet-user prompt:")
            result = await session.get_prompt("greet-user", {"name": "Alice", "style": "formal"})
            for message in result.messages:
                print(f"[{message.role}] {message.content.text}")

            # Fetch a weather prompt
            print("\nFetching ask-weather prompt:")
            result = await session.get_prompt("ask-weather", {"city": "Chennai"})
            for message in result.messages:
                print(f"[{message.role}] {message.content.text}")

asyncio.run(run())
