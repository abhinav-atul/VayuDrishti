"""
WAQI (World Air Quality Index) API Client
Fetches real-time air quality data from monitoring stations in Delhi.
"""

import time
import httpx
from app.config import settings
from app.schemas import StationReading

# In-memory cache
_cache: dict = {"stations": [], "timestamp": 0}


def _pm25_to_aqi(pm25: float) -> int:
    """Convert PM2.5 concentration (µg/m³) to India's National AQI.
    
    Uses the Indian National AQI breakpoints for PM2.5 (24-hr average).
    """
    breakpoints = [
        (0, 30, 0, 50),        # Good
        (31, 60, 51, 100),     # Satisfactory
        (61, 90, 101, 200),    # Moderate
        (91, 120, 201, 300),   # Poor
        (121, 250, 301, 400),  # Very Poor
        (251, 500, 401, 500),  # Severe
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if pm25 <= bp_hi:
            return round(aqi_lo + (pm25 - bp_lo) * (aqi_hi - aqi_lo) / (bp_hi - bp_lo))
    return 500  # Beyond severe


def _aqi_category(aqi: int) -> str:
    """Map AQI value to category string."""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"


def _aqi_color(aqi: int) -> str:
    """Map AQI value to hex color (India NAQI standard colors)."""
    if aqi <= 50:
        return "#10b981"   # Green - Good
    elif aqi <= 100:
        return "#84cc16"   # Lime - Satisfactory
    elif aqi <= 200:
        return "#eab308"   # Yellow - Moderate
    elif aqi <= 300:
        return "#f97316"   # Orange - Poor
    elif aqi <= 400:
        return "#ef4444"   # Red - Very Poor
    else:
        return "#991b1b"   # Dark Red - Severe


def _health_advisory(aqi: int) -> str:
    """Return health advisory based on AQI level."""
    if aqi <= 50:
        return "Air quality is satisfactory. Ideal for outdoor activities."
    elif aqi <= 100:
        return "Air quality is acceptable. Sensitive individuals should limit prolonged outdoor exertion."
    elif aqi <= 200:
        return "May cause breathing discomfort to people with lung disease, asthma, and heart disease. Minimize outdoor activities."
    elif aqi <= 300:
        return "May cause breathing discomfort on prolonged exposure. Avoid outdoor activities, especially for children and elderly."
    elif aqi <= 400:
        return "May cause respiratory illness on prolonged exposure. Avoid all outdoor physical activities."
    else:
        return "Severe health impacts likely. Stay indoors. Keep windows closed. Use air purifier if available."


async def fetch_delhi_stations() -> list[StationReading]:
    """Fetch real-time AQI data for all Delhi monitoring stations from WAQI.
    
    Uses bounding box search to find all stations in Delhi.
    Results are cached for WAQI_CACHE_TTL seconds.
    """
    now = time.time()
    if _cache["stations"] and (now - _cache["timestamp"]) < settings.WAQI_CACHE_TTL:
        return _cache["stations"]

    token = settings.WAQI_TOKEN
    if not token or token == "your_waqi_token_here":
        # Return demo data if no token configured
        return _get_demo_stations()

    bbox = settings.DELHI_BBOX
    url = (
        f"https://api.waqi.info/v2/map/bounds/"
        f"?latlng={bbox['lat_min']},{bbox['lng_min']},"
        f"{bbox['lat_max']},{bbox['lng_max']}"
        f"&networks=all&token={token}"
    )

    stations = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                print(f"WAQI API error: {data}")
                return _get_demo_stations()

            for item in data.get("data", []):
                aqi_val = item.get("aqi")
                if aqi_val == "-" or aqi_val is None:
                    continue
                try:
                    aqi_int = int(aqi_val)
                except (ValueError, TypeError):
                    continue

                station = StationReading(
                    station_id=str(item.get("uid", "")),
                    name=item.get("station", {}).get("name", "Unknown"),
                    lat=item.get("lat", 0),
                    lng=item.get("lon", 0),
                    aqi=aqi_int,
                    timestamp=item.get("station", {}).get("time", ""),
                )
                stations.append(station)

        # Fetch detailed data for each station to get individual pollutants
        detailed_stations = []
        async with httpx.AsyncClient(timeout=10) as client:
            for station in stations[:50]:  # Limit to avoid rate issues
                try:
                    detail_url = f"https://api.waqi.info/feed/@{station.station_id}/?token={token}"
                    resp = await client.get(detail_url)
                    if resp.status_code == 200:
                        detail = resp.json()
                        if detail.get("status") == "ok":
                            d = detail["data"]
                            iaqi = d.get("iaqi", {})
                            station.pm25 = iaqi.get("pm25", {}).get("v")
                            station.pm10 = iaqi.get("pm10", {}).get("v")
                            station.no2 = iaqi.get("no2", {}).get("v")
                            station.so2 = iaqi.get("so2", {}).get("v")
                            station.o3 = iaqi.get("o3", {}).get("v")
                            station.co = iaqi.get("co", {}).get("v")
                            station.temperature = iaqi.get("t", {}).get("v")
                            station.humidity = iaqi.get("h", {}).get("v")
                            station.wind_speed = iaqi.get("w", {}).get("v")
                except Exception:
                    pass  # Skip failed detail fetches, keep basic data
                detailed_stations.append(station)

        stations = detailed_stations if detailed_stations else stations

    except Exception as e:
        print(f"WAQI fetch failed: {e}")
        return _get_demo_stations()

    _cache["stations"] = stations
    _cache["timestamp"] = now
    return stations


def _get_demo_stations() -> list[StationReading]:
    """Fallback demo data based on real Delhi CPCB station locations and typical readings."""
    demo_data = [
        ("Anand Vihar", 28.6469, 77.3164, 287, 189),
        ("ITO", 28.6289, 77.2415, 234, 156),
        ("RK Puram", 28.5635, 77.1868, 198, 132),
        ("Dwarka Sector 8", 28.5721, 77.0688, 176, 118),
        ("Mandir Marg", 28.6363, 77.2009, 165, 109),
        ("Punjabi Bagh", 28.6683, 77.1167, 245, 163),
        ("Rohini", 28.7328, 77.1167, 223, 148),
        ("Nehru Nagar", 28.5680, 77.2500, 201, 134),
        ("Patparganj", 28.6237, 77.2872, 256, 170),
        ("Wazirpur", 28.6997, 77.1652, 267, 178),
        ("Jahangirpuri", 28.7269, 77.1726, 234, 156),
        ("Vivek Vihar", 28.6729, 77.3153, 278, 185),
        ("Mundka", 28.6821, 77.0266, 198, 132),
        ("Okhla Phase 2", 28.5308, 77.2713, 212, 141),
        ("Siri Fort", 28.5494, 77.2156, 178, 119),
        ("North Campus DU", 28.6883, 77.2096, 192, 128),
        ("Shadipur", 28.6514, 77.1579, 209, 139),
        ("Bawana", 28.7762, 77.0510, 245, 163),
        ("Narela", 28.8227, 77.1025, 220, 146),
        ("Najafgarh", 28.5693, 77.0085, 186, 124),
        ("Alipur", 28.7950, 77.1530, 210, 140),
        ("Ashok Vihar", 28.6940, 77.1820, 238, 158),
        ("Aya Nagar", 28.4710, 77.1340, 168, 112),
        ("Burari Crossing", 28.7250, 77.2000, 228, 152),
        ("CRRI Mathura Road", 28.5510, 77.2740, 195, 130),
        ("DTU", 28.7500, 77.1170, 215, 143),
        ("East Arjun Nagar", 28.6560, 77.2930, 262, 174),
        ("IGI Airport T3", 28.5562, 77.0872, 172, 115),
        ("IHBAS Dilshad Garden", 28.6810, 77.3020, 248, 165),
        ("JLN Stadium", 28.5870, 77.2340, 188, 125),
        ("Lodhi Road", 28.5916, 77.2273, 175, 117),
        ("Major Dhyan Chand Stadium", 28.6100, 77.2370, 182, 121),
        ("NSIT Dwarka", 28.6090, 77.0328, 169, 113),
        ("Pusa DPCC", 28.6395, 77.1462, 196, 131),
        ("Sonia Vihar", 28.7140, 77.2490, 237, 158),
        ("Sri Aurobindo Marg", 28.5310, 77.1900, 173, 116),
    ]

    stations = []
    import random
    for i, (name, lat, lng, aqi, pm25) in enumerate(demo_data):
        # Add slight randomness to make demo feel alive
        jitter = random.uniform(0.9, 1.1)
        stations.append(StationReading(
            station_id=str(1000 + i),
            name=f"{name}, Delhi",
            lat=lat,
            lng=lng,
            aqi=int(aqi * jitter),
            pm25=round(pm25 * jitter, 1),
            pm10=round(pm25 * 1.6 * jitter, 1),
            no2=round(35 * jitter, 1),
            so2=round(12 * jitter, 1),
            o3=round(28 * jitter, 1),
            co=round(1.8 * jitter, 2),
            temperature=round(32 + random.uniform(-3, 3), 1),
            humidity=round(55 + random.uniform(-10, 10), 1),
            wind_speed=round(2.5 + random.uniform(-1, 2), 1),
            wind_direction=round(random.uniform(180, 300)),
            timestamp="2026-07-21T12:00:00+05:30",
        ))
    return stations
