#mcpclient.py
import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_core.callbacks import AsyncCallbackHandler

from dotenv import load_dotenv
load_dotenv()
 

# Callback to log tool calls for debugging
# This logs every tool invocation (tool name and input parameters).
# Useful for debugging how the agent is using your tools.
class ToolCallLogger(AsyncCallbackHandler):
    async def on_tool_start(self, serialized: dict, input: dict, **kwargs) -> None:
        print(f"Tool called: {serialized.get('name')} with input: {input}")
 

async def main():

    # Create MCP client
    client = MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                "args": ["C:/Users/sonal.binji/Documents/mcp/try1/math_server.py"],
                "transport": "stdio",
            },
            "weather": {
                "command": "python",
                "args": ["C:/Users/sonal.binji/Documents/mcp/try1/weather_server.py"],
                "transport": "stdio", 
            }
        }
    )
 
    # Get available tools from MCP server
    tools = await client.get_tools()
 
    # Groq LLM setup with system prompt
    system_prompt = (
        "You are a math assistant. For expressions like (a + b) x c, first compute the addition (a + b) using the 'add' tool, "
        "then use the result with the 'multiply' tool to multiply by c. Ensure all tool inputs are integers."
    )
    groq_llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile", 
    )
 
    # Create ReAct agent with Groq + MCP tools
    agent = create_react_agent(model=groq_llm, tools=tools)
 
    # Run the agent with the system prompt included in the messages
    math_response = await agent.ainvoke(
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "what's (3 + 5) x 12?"}
            ]
        },
        config={"callbacks": [ToolCallLogger()]}  # Add callback for debugging
    )
    print(f"Final Answer: ", math_response['messages'][-1].content)
 
    # Example of calling weather tool
    weather_response = await agent.ainvoke(    
        {
            "messages": [
                {"role": "system", "content": "You are a weather assistant with real-time weather information."},
                {"role": "user", "content": "What's the weather in Chennai?"}
            ]
        },
        config={"callbacks": [ToolCallLogger()]}  # Add callback for debugging
    )
    print(f"Weather Response: ", weather_response['messages'][-1].content)


if __name__ == "__main__":
    asyncio.run(main())