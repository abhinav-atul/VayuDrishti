"""
OpenWeatherMap API Client
Fetches current weather and air pollution forecast for Delhi.
"""

import time
import httpx
from app.config import settings

_weather_cache: dict = {"data": None, "timestamp": 0}
_pollution_cache: dict = {"data": None, "timestamp": 0}

# Delhi center coordinates
DELHI_LAT = 28.6139
DELHI_LNG = 77.2090


async def fetch_weather() -> dict:
    """Fetch current weather conditions for Delhi.
    
    Returns dict with temperature, humidity, wind_speed, wind_direction, pressure.
    """
    now = time.time()
    if _weather_cache["data"] and (now - _weather_cache["timestamp"]) < settings.WEATHER_CACHE_TTL:
        return _weather_cache["data"]

    api_key = settings.OWM_API_KEY
    if not api_key or api_key == "your_owm_key_here":
        return _demo_weather()

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={DELHI_LAT}&lon={DELHI_LNG}"
        f"&appid={api_key}&units=metric"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            result = {
                "temperature": data.get("main", {}).get("temp", 32),
                "humidity": data.get("main", {}).get("humidity", 55),
                "pressure": data.get("main", {}).get("pressure", 1012),
                "wind_speed": data.get("wind", {}).get("speed", 2.5),
                "wind_direction": data.get("wind", {}).get("deg", 240),
                "description": data.get("weather", [{}])[0].get("description", ""),
            }

            _weather_cache["data"] = result
            _weather_cache["timestamp"] = now
            return result

    except Exception as e:
        print(f"OWM weather fetch failed: {e}")
        return _demo_weather()


async def fetch_air_pollution_forecast() -> list[dict]:
    """Fetch 4-day hourly air pollution forecast from OWM.
    
    Returns list of dicts with timestamp, aqi, pm25, pm10, no2, so2, o3, co.
    Used as a comparison baseline for our model.
    """
    now = time.time()
    if _pollution_cache["data"] and (now - _pollution_cache["timestamp"]) < settings.WEATHER_CACHE_TTL:
        return _pollution_cache["data"]

    api_key = settings.OWM_API_KEY
    if not api_key or api_key == "your_owm_key_here":
        return []

    url = (
        f"https://api.openweathermap.org/data/2.5/air_pollution/forecast"
        f"?lat={DELHI_LAT}&lon={DELHI_LNG}"
        f"&appid={api_key}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            forecasts = []
            for item in data.get("list", []):
                components = item.get("components", {})
                forecasts.append({
                    "timestamp": item.get("dt", 0),
                    "owm_aqi": item.get("main", {}).get("aqi", 0),
                    "pm25": components.get("pm2_5", 0),
                    "pm10": components.get("pm10", 0),
                    "no2": components.get("no2", 0),
                    "so2": components.get("so2", 0),
                    "o3": components.get("o3", 0),
                    "co": components.get("co", 0),
                })

            _pollution_cache["data"] = forecasts
            _pollution_cache["timestamp"] = now
            return forecasts

    except Exception as e:
        print(f"OWM pollution forecast fetch failed: {e}")
        return []


def _demo_weather() -> dict:
    """Fallback demo weather data for Delhi in July."""
    import random
    return {
        "temperature": round(33 + random.uniform(-2, 3), 1),
        "humidity": round(62 + random.uniform(-8, 12), 1),
        "pressure": 1008,
        "wind_speed": round(2.8 + random.uniform(-1, 2), 1),
        "wind_direction": round(225 + random.uniform(-30, 30)),
        "description": "haze",
    }
