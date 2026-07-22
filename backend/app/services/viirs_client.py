"""
NASA FIRMS (VIIRS) Client
Fetches near real-time fire/thermal anomaly detections for Delhi region.
"""

import time
import io
import httpx
import pandas as pd
from app.config import settings
from app.schemas import FireHotspot

_cache: dict = {"fires": [], "timestamp": 0}


async def fetch_fires() -> list[FireHotspot]:
    """Fetch active fire detections from NASA VIIRS within Delhi bounding box.
    
    VIIRS I-Band detects fires at 375m resolution with ~3 hour latency.
    Returns fire hotspots with location, brightness, FRP, and confidence.
    """
    now = time.time()
    if _cache["fires"] and (now - _cache["timestamp"]) < settings.VIIRS_CACHE_TTL:
        return _cache["fires"]

    map_key = settings.FIRMS_MAP_KEY
    if not map_key or map_key == "your_firms_key_here":
        return _get_demo_fires()

    bbox = settings.DELHI_BBOX
    # FIRMS API: area endpoint with bounding box, last 2 days
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/VIIRS_SNPP_NRT/"
        f"{bbox['lng_min']},{bbox['lat_min']},"
        f"{bbox['lng_max']},{bbox['lat_max']}/2"
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            # Parse CSV response
            df = pd.read_csv(io.StringIO(resp.text))
            if df.empty:
                return []

            fires = []
            for _, row in df.iterrows():
                fires.append(FireHotspot(
                    lat=float(row.get("latitude", 0)),
                    lng=float(row.get("longitude", 0)),
                    brightness=float(row.get("bright_ti4", 0)),
                    frp=float(row.get("frp", 0)),
                    confidence=str(row.get("confidence", "nominal")),
                    acq_date=str(row.get("acq_date", "")),
                    acq_time=str(row.get("acq_time", "")),
                ))

            _cache["fires"] = fires
            _cache["timestamp"] = now
            return fires

    except Exception as e:
        print(f"FIRMS fetch failed: {e}")
        return _get_demo_fires()


def _get_demo_fires() -> list[FireHotspot]:
    """Fallback demo fire data — typical burning locations around Delhi."""
    return [
        FireHotspot(
            lat=28.7100, lng=77.3280,
            brightness=330.5, frp=18.2,
            confidence="high", acq_date="2026-07-21", acq_time="0530"
        ),
        FireHotspot(
            lat=28.6250, lng=77.3450,
            brightness=315.8, frp=12.4,
            confidence="nominal", acq_date="2026-07-21", acq_time="0530"
        ),
        FireHotspot(
            lat=28.5780, lng=77.0320,
            brightness=342.1, frp=24.8,
            confidence="high", acq_date="2026-07-21", acq_time="0530"
        ),
        FireHotspot(
            lat=28.7900, lng=77.0800,
            brightness=310.2, frp=8.9,
            confidence="nominal", acq_date="2026-07-21", acq_time="1730"
        ),
        FireHotspot(
            lat=28.8100, lng=77.2100,
            brightness=325.7, frp=15.3,
            confidence="high", acq_date="2026-07-21", acq_time="1730"
        ),
        FireHotspot(
            lat=28.4800, lng=77.1500,
            brightness=308.4, frp=7.2,
            confidence="low", acq_date="2026-07-20", acq_time="0530"
        ),
    ]
