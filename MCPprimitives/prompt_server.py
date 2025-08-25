# prompt_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PromptsDemo")

# Example prompt: greet a user
@mcp.prompt("greet-user")
def greet_user(name: str = "You", style: str = "friendly") -> str:
    """Prompt to greet a user in different styles."""
    if style == "friendly":
        return f"Hey {name}! Hope you're doing great today! 😊"
    elif style == "formal":
        return f"Good day, {name}. I hope this message finds you well."
    else:
        return f"Hello {name}!"

# Example prompt: ask about weather
@mcp.prompt("ask-weather")
def ask_weather(city: str) -> str:
    """Prompt to ask about weather in a given city."""
    return f"Could you tell me the current weather in {city}?"

if __name__ == "__main__":
    mcp.run(transport="stdio")
