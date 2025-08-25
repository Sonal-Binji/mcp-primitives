from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather + Info")

# --- Static Resource ---
@mcp.resource("about://info")
def get_info() -> str:
    """Static resource: general information about this server."""
    return "This is the Weather + Info MCP server. It provides static info and dynamic weather reports."

# --- Dynamic Resource ---
@mcp.resource("weather://{city}")
def get_weather(city: str) -> str:
    """Dynamic resource: fetch simulated weather for a city."""
    return f"Simulated weather report for {city}"

if __name__ == "__main__":
    mcp.run(transport="stdio")