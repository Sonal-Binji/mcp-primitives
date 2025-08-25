import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["resource_server.py"]
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # --- Static Resources ---
            resources = await session.list_resources()
            print("Static Resources:")
            for r in resources.resources:
                print("-", r.uri)

            # Fetch static resource(s)
            for r in resources.resources:
                result = await session.read_resource(r.uri)
                for content in result.contents:
                    print(f"[{content.uri}] =>", content.text)

            # --- Dynamic Resource Templates ---
            templates = await session.list_resource_templates()
            print("\nDynamic Templates:")
            for t in templates.resourceTemplates:
                print("-", t.uriTemplate)

            # Fetch dynamic resource (example: weather://Paris)
            for t in templates.resourceTemplates:
                if "{city}" in t.uriTemplate:
                    uri = t.uriTemplate.replace("{city}", "Paris")
                    result = await session.read_resource(uri)
                    for content in result.contents:
                        print(f"[{content.uri}] =>", content.text)

asyncio.run(run())
