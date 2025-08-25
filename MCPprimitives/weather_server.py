# weather_server.py
import os
import requests
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()  # Load your WEATHER_API_KEY from .env

mcp = FastMCP("Weather")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get real-time weather for a given location."""
    if not WEATHER_API_KEY:
        raise ValueError("WEATHER_API_KEY is not set in the environment variables.")
    
    try:
        url = f"http://api.weatherapi.com/v1/current.json"
        params = {
            "key": WEATHER_API_KEY, 
            "q": location, 
            "aqi": "no"
            }
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        if "error" in data:
            message = data["error"].get("message", "Unknown error")
            return f"Could not fetch weather for '{location}': {message}"
        
        location_name = data["location"]["name"]
        temperature = data["current"]["temp_c"]
        condition = data["current"]["condition"]["text"]
        humidity = data["current"]["humidity"]
        wind_speed = data["current"]["wind_kph"]

        return (
            f"Weather in {location_name}:\n"
            f" - Temperature: {temperature}°C\n"
            f" - Condition: {condition}\n"
            f" - Humidity: {humidity}%\n"
            f" - Wind Speed: {wind_speed} km/h"
        )

    except requests.RequestException as e:
        return f"Failed to fetch weather data: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")  # Use stdio transport
