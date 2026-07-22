"""
Grid Engine — The Core of VayuDrishti

Constructs a 1km×1km grid over Delhi and assembles the feature matrix
for each cell. This is the input to the XGBoost spatial prediction model.
"""

import math
import numpy as np
import pandas as pd
import time
from app.config import settings
from app.schemas import StationReading, FireHotspot

_grid_cache: dict = {"features": None, "timestamp": 0}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in kilometers."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_grid() -> list[dict]:
    """Construct the 1km×1km grid cells over Delhi.
    
    Returns list of dicts with row, col, center_lat, center_lng for each cell.
    """
    bbox = settings.DELHI_BBOX
    res = settings.GRID_RESOLUTION

    cells = []
    row = 0
    lat = bbox["lat_min"]
    while lat < bbox["lat_max"]:
        col = 0
        lng = bbox["lng_min"]
        while lng < bbox["lng_max"]:
            cells.append({
                "row": row,
                "col": col,
                "lat": round(lat + res / 2, 5),  # Cell center
                "lng": round(lng + res / 2, 5),
                "lat_min": lat,
                "lat_max": lat + res,
                "lng_min": lng,
                "lng_max": lng + res,
            })
            lng += res
            col += 1
        lat += res
        row += 1

    return cells


def compute_station_features(
    cell_lat: float,
    cell_lng: float,
    stations: list[StationReading],
    k: int = 5,
) -> dict:
    """Compute station-derived features for a single grid cell.
    
    Features:
    - nearest_station_pm25: PM2.5 of closest station
    - nearest_station_dist_km: distance to closest station
    - idw_pm25: Inverse Distance Weighted PM2.5 from k nearest stations
    - station_count_10km: number of stations within 10km
    """
    if not stations:
        return {
            "nearest_station_pm25": 150.0,
            "nearest_station_dist_km": 20.0,
            "nearest_station_name": "Unknown",
            "idw_pm25": 150.0,
            "station_count_10km": 0,
        }

    # Calculate distances to all stations
    dists = []
    for s in stations:
        if s.pm25 is not None and s.pm25 > 0:
            d = haversine_km(cell_lat, cell_lng, s.lat, s.lng)
            dists.append((d, s))

    if not dists:
        return {
            "nearest_station_pm25": 150.0,
            "nearest_station_dist_km": 20.0,
            "nearest_station_name": "Unknown",
            "idw_pm25": 150.0,
            "station_count_10km": 0,
        }

    dists.sort(key=lambda x: x[0])

    nearest_dist, nearest_station = dists[0]

    # IDW interpolation from k nearest stations
    top_k = dists[:k]
    idw_numerator = 0.0
    idw_denominator = 0.0
    for dist, station in top_k:
        # Avoid division by zero — if we're right on a station
        w = 1.0 / max(dist, 0.01) ** 2
        idw_numerator += w * station.pm25
        idw_denominator += w

    idw_pm25 = idw_numerator / idw_denominator if idw_denominator > 0 else 150.0

    # Count stations within 10km
    count_10km = sum(1 for d, _ in dists if d <= 10.0)

    return {
        "nearest_station_pm25": nearest_station.pm25,
        "nearest_station_dist_km": round(nearest_dist, 2),
        "nearest_station_name": nearest_station.name,
        "idw_pm25": round(idw_pm25, 1),
        "station_count_10km": count_10km,
    }


def compute_fire_features(
    cell_lat: float,
    cell_lng: float,
    fires: list[FireHotspot],
    radius_km: float = 10.0,
) -> dict:
    """Compute fire-derived features for a grid cell.
    
    Features:
    - fire_count_10km: number of VIIRS fire detections within radius
    - fire_frp_sum_10km: total Fire Radiative Power within radius
    - nearest_fire_dist_km: distance to closest fire
    """
    if not fires:
        return {
            "fire_count_10km": 0,
            "fire_frp_sum_10km": 0.0,
            "nearest_fire_dist_km": 50.0,
        }

    fire_count = 0
    frp_sum = 0.0
    min_fire_dist = 999.0

    for fire in fires:
        d = haversine_km(cell_lat, cell_lng, fire.lat, fire.lng)
        if d < min_fire_dist:
            min_fire_dist = d
        if d <= radius_km:
            fire_count += 1
            frp_sum += fire.frp

    return {
        "fire_count_10km": fire_count,
        "fire_frp_sum_10km": round(frp_sum, 1),
        "nearest_fire_dist_km": round(min_fire_dist, 1),
    }


def compute_temporal_features() -> dict:
    """Compute time-based features with cyclical encoding."""
    from datetime import datetime
    now = datetime.now()

    hour = now.hour
    dow = now.weekday()
    month = now.month

    return {
        "hour_sin": round(math.sin(2 * math.pi * hour / 24), 4),
        "hour_cos": round(math.cos(2 * math.pi * hour / 24), 4),
        "day_of_week": dow,
        "month": month,
        "is_winter": 1 if month in [10, 11, 12, 1, 2] else 0,
        "is_rush_hour": 1 if hour in [7, 8, 9, 17, 18, 19] else 0,
    }


def compute_spatial_features(cell_lat: float, cell_lng: float) -> dict:
    """Compute static spatial features for a grid cell.
    
    Simplified version using coordinate-based heuristics for Delhi.
    In production, this would use actual OSM data / GeoJSON intersection.
    
    For the hackathon, we estimate:
    - road_density: based on proximity to known major roads/highways
    - industrial_pct: based on known industrial zones
    - green_cover_pct: based on known parks/forests
    - distance_to_highway: distance to nearest major highway
    """
    # Major Delhi highways (approximate centerlines)
    highways = [
        # NH-44 (GT Road) — roughly north-south through east Delhi
        (28.40, 77.30, 28.88, 77.32),
        # NH-48 (Delhi-Jaipur) — southwest
        (28.52, 76.90, 28.62, 77.20),
        # Ring Road — approximated as segments
        (28.55, 77.15, 28.70, 77.15),
        (28.55, 77.25, 28.70, 77.25),
        # Outer Ring Road
        (28.50, 77.05, 28.78, 77.05),
        (28.50, 77.35, 28.78, 77.35),
    ]

    min_highway_dist = 50.0
    for lat1, lng1, lat2, lng2 in highways:
        # Point-to-line-segment distance approximation
        mid_lat = (lat1 + lat2) / 2
        mid_lng = (lng1 + lng2) / 2
        d = haversine_km(cell_lat, cell_lng, mid_lat, mid_lng)
        if d < min_highway_dist:
            min_highway_dist = d

    # Known industrial zones in Delhi (approximate centroids)
    industrial_zones = [
        (28.6821, 77.0266, 2.0),   # Mundka
        (28.7328, 77.1167, 1.5),   # Bawana/Narela industrial
        (28.6997, 77.1652, 1.5),   # Wazirpur industrial
        (28.5308, 77.2713, 1.5),   # Okhla industrial
        (28.6683, 77.3164, 1.5),   # Patparganj industrial
        (28.6940, 77.0700, 2.0),   # Badli industrial
        (28.6300, 77.3500, 1.5),   # Sahibabad (near border)
    ]

    near_industrial = 0.0
    for iz_lat, iz_lng, iz_radius in industrial_zones:
        d = haversine_km(cell_lat, cell_lng, iz_lat, iz_lng)
        if d <= iz_radius:
            near_industrial = max(near_industrial, 1.0 - d / iz_radius)

    # Known green areas
    green_zones = [
        (28.5950, 77.1740, 2.0),   # Ridge (central)
        (28.5210, 77.1850, 1.5),   # Sanjay Van
        (28.5570, 77.2500, 1.0),   # Lodhi Garden area
        (28.6060, 77.2220, 0.5),   # India Gate lawns
        (28.7350, 77.2100, 1.5),   # Kamla Nehru Ridge
        (28.5800, 77.0400, 1.5),   # Dwarka green belt
    ]

    near_green = 0.0
    for g_lat, g_lng, g_radius in green_zones:
        d = haversine_km(cell_lat, cell_lng, g_lat, g_lng)
        if d <= g_radius:
            near_green = max(near_green, 1.0 - d / g_radius)

    # Road density heuristic: higher near center, lower at periphery
    dist_to_center = haversine_km(cell_lat, cell_lng, 28.6139, 77.2090)
    road_density = max(0.1, 1.0 - dist_to_center / 25.0)

    return {
        "road_density": round(road_density, 3),
        "industrial_proximity": round(near_industrial, 3),
        "green_cover_proximity": round(near_green, 3),
        "distance_to_highway_km": round(min_highway_dist, 2),
        "distance_to_center_km": round(dist_to_center, 2),
    }


def build_feature_matrix(
    stations: list[StationReading],
    fires: list[FireHotspot],
    weather: dict,
    satellite_data: dict | None = None,
) -> pd.DataFrame:
    """Build the complete feature matrix for the entire Delhi grid.
    
    Each row = one grid cell with all features assembled.
    This is the input to the ML model for inference.
    """
    from app.services.satellite import get_satellite_value, _get_baseline_data

    cells = build_grid()
    temporal = compute_temporal_features()
    sat_data = satellite_data if satellite_data else _get_baseline_data()

    rows = []
    for cell in cells:
        lat, lng = cell["lat"], cell["lng"]

        station_feats = compute_station_features(lat, lng, stations)
        fire_feats = compute_fire_features(lat, lng, fires)
        spatial_feats = compute_spatial_features(lat, lng)
        sat_feats = get_satellite_value(lat, lng, sat_data)

        row = {
            "row": cell["row"],
            "col": cell["col"],
            "lat": lat,
            "lng": lng,
            # Station features
            **station_feats,
            # Fire features
            **fire_feats,
            # Spatial features
            **spatial_feats,
            # Satellite features (Sentinel-5P)
            **sat_feats,
            # Weather features (city-wide)
            "temperature": weather.get("temperature", 32),
            "humidity": weather.get("humidity", 55),
            "wind_speed": weather.get("wind_speed", 2.5),
            "wind_direction": weather.get("wind_direction", 240),
            "pressure": weather.get("pressure", 1012),
            # Temporal features
            **temporal,
        }
        rows.append(row)

    return pd.DataFrame(rows)


# The feature columns the model uses (in order)
FEATURE_COLUMNS = [
    "nearest_station_pm25",
    "nearest_station_dist_km",
    "idw_pm25",
    "station_count_10km",
    "fire_count_10km",
    "fire_frp_sum_10km",
    "nearest_fire_dist_km",
    "road_density",
    "industrial_proximity",
    "green_cover_proximity",
    "distance_to_highway_km",
    "distance_to_center_km",
    "satellite_no2",
    "satellite_so2",
    "satellite_aerosol",
    "temperature",
    "humidity",
    "wind_speed",
    "wind_direction",
    "pressure",
    "hour_sin",
    "hour_cos",
    "day_of_week",
    "month",
    "is_winter",
    "is_rush_hour",
]
