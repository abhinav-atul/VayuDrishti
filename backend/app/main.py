"""
VayuDrishti — Hyperlocal Air Quality Intelligence for Delhi
FastAPI Application Entry Point
"""

import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import (
    ChatRequest, ChatResponse, PointEstimate,
    GridResponse, ModelMetrics, FireHotspot, StationReading,
)
from app.services import waqi_client, weather_client, viirs_client
from app.services import satellite as satellite_client
from app.services.grid_engine import build_feature_matrix, FEATURE_COLUMNS
from app.services import predictor
from app.services import chat_service


# Cached state
_grid_cache = {"geojson": None, "feature_df": None, "stations": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load ML model, warm caches."""
    print("[VayuDrishti] Starting up...")
    predictor.load_model()

    # Initial data fetch and grid computation
    try:
        await _refresh_grid()
        print("[OK] Grid computed and cached")
    except Exception as e:
        print(f"[WARN] Initial grid computation failed: {e}")

    yield
    print("VayuDrishti shutting down.")


app = FastAPI(
    title="VayuDrishti API",
    description="Hyperlocal Air Quality Intelligence for Delhi — Spatial ML fusion of ground stations, satellite data, and fire hotspots.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _refresh_grid():
    """Fetch fresh data and recompute the grid predictions."""
    stations = await waqi_client.fetch_delhi_stations()
    weather = await weather_client.fetch_weather()
    fires = await viirs_client.fetch_fires()
    sat_data = await satellite_client.fetch_satellite_data()

    feature_df = build_feature_matrix(stations, fires, weather, satellite_data=sat_data)

    # If no trained model, auto-train on current data
    if predictor._model is None:
        print("[ML] No model found -- training on current station data...")
        training_data = predictor.generate_training_data(stations, fires, weather)
        if len(training_data) >= 5:
            predictor.train_model(training_data)
            print(f"[OK] Model trained on {len(training_data)} station observations")
        else:
            print("[WARN] Not enough stations with PM2.5 data to train. Using IDW fallback.")

    grid_cells = predictor.predict_grid(feature_df)

    # Build GeoJSON FeatureCollection
    features = []
    res = settings.GRID_RESOLUTION
    for cell in grid_cells:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [cell.lng - res / 2, cell.lat - res / 2],
                    [cell.lng + res / 2, cell.lat - res / 2],
                    [cell.lng + res / 2, cell.lat + res / 2],
                    [cell.lng - res / 2, cell.lat + res / 2],
                    [cell.lng - res / 2, cell.lat - res / 2],
                ]],
            },
            "properties": {
                "pm25": cell.predicted_pm25,
                "aqi": cell.predicted_aqi,
                "category": cell.aqi_category,
                "confidence": cell.confidence,
                "nearest_dist": cell.nearest_station_dist_km,
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    _grid_cache["geojson"] = geojson
    _grid_cache["feature_df"] = feature_df
    _grid_cache["stations"] = stations


# ─── Grid Routes ──────────────────────────────────────────────────────────

@app.get("/api/grid", tags=["Grid"])
async def get_grid():
    """Get the full prediction grid as GeoJSON.
    
    Each cell is a 1km×1km polygon with predicted PM2.5 and AQI.
    """
    if _grid_cache["geojson"] is None:
        await _refresh_grid()
    return _grid_cache["geojson"]


@app.get("/api/point", response_model=PointEstimate, tags=["Grid"])
async def get_point_estimate(
    lat: float = Query(..., ge=28.0, le=29.0, description="Latitude"),
    lng: float = Query(..., ge=76.0, le=78.0, description="Longitude"),
):
    """Get PM2.5 estimate at any arbitrary coordinate in Delhi.
    
    This is the core feature: click anywhere on the map and get an air quality estimate.
    """
    if _grid_cache["feature_df"] is None:
        await _refresh_grid()

    result = predictor.predict_point(
        lat, lng,
        _grid_cache["feature_df"],
        _grid_cache["stations"],
    )
    return PointEstimate(**result)


# ─── Station Routes ────────────────────────────────────────────────────

@app.get("/api/stations", response_model=list[StationReading], tags=["Stations"])
async def get_stations():
    """Get all Delhi monitoring station readings (ground truth)."""
    return await waqi_client.fetch_delhi_stations()


# ─── Fire Routes ───────────────────────────────────────────────────────

@app.get("/api/fires", response_model=list[FireHotspot], tags=["Fires"])
async def get_fires():
    """Get active VIIRS fire/thermal anomaly detections near Delhi."""
    return await viirs_client.fetch_fires()


# ─── Model Routes ──────────────────────────────────────────────────────

@app.get("/api/model/metrics", tags=["Model"])
async def get_model_metrics():
    """Get LOSO cross-validation results and feature importance.
    
    This endpoint provides scientific validation that the model
    can predict AQI at locations it has never seen.
    """
    validation = {}
    importance = []

    if settings.VALIDATION_PATH.exists():
        with open(settings.VALIDATION_PATH) as f:
            validation = json.load(f)

    if settings.SHAP_PATH.exists():
        with open(settings.SHAP_PATH) as f:
            importance = json.load(f)

    return {
        "validation": validation,
        "feature_importance": importance,
        "model_loaded": predictor._model is not None,
    }


@app.post("/api/model/train", tags=["Model"])
async def trigger_training():
    """Manually trigger model training on current station data."""
    stations = await waqi_client.fetch_delhi_stations()
    weather = await weather_client.fetch_weather()
    fires = await viirs_client.fetch_fires()

    training_data = predictor.generate_training_data(stations, fires, weather)

    if len(training_data) < 5:
        return {"error": "Not enough stations with PM2.5 data", "count": len(training_data)}

    # Train
    predictor.train_model(training_data)

    # Run LOSO validation
    validation = predictor.loso_cross_validate(training_data)

    # Refresh grid with new model
    await _refresh_grid()

    return {
        "message": "Model trained and grid refreshed",
        "training_samples": len(training_data),
        "validation": validation,
    }


# ─── Chat Routes ───────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_advisory(request: ChatRequest):
    """Get AI-powered air quality advisory.
    
    Optionally provide lat/lng to get location-specific advice
    based on the model's prediction at that point.
    """
    aqi_context = None

    if request.lat is not None and request.lng is not None:
        if _grid_cache["feature_df"] is None:
            await _refresh_grid()

        aqi_context = predictor.predict_point(
            request.lat, request.lng,
            _grid_cache["feature_df"],
            _grid_cache["stations"],
        )

        # Add city-wide stats
        stations = _grid_cache["stations"]
        if stations:
            valid_stations = [s for s in stations if s.aqi and s.aqi > 0]
            if valid_stations:
                avg_aqi = sum(s.aqi for s in valid_stations) / len(valid_stations)
                worst = max(valid_stations, key=lambda s: s.aqi)
                best = min(valid_stations, key=lambda s: s.aqi)
                aqi_context["city_stats"] = {
                    "avg_aqi": round(avg_aqi),
                    "worst_station": f"{worst.name} (AQI {worst.aqi})",
                    "best_station": f"{best.name} (AQI {best.aqi})",
                }

    result = await chat_service.get_advisory(
        message=request.message,
        aqi_context=aqi_context,
        language=request.language,
    )

    return ChatResponse(**result)


# ─── Health Check ──────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check."""
    return {
        "status": "ok",
        "model_loaded": predictor._model is not None,
        "grid_cached": _grid_cache["geojson"] is not None,
        "stations_cached": len(_grid_cache["stations"]) if _grid_cache["stations"] else 0,
    }


@app.get("/api/refresh", tags=["System"])
async def refresh_data():
    """Force refresh all data and recompute the grid."""
    await _refresh_grid()
    return {
        "message": "Data refreshed and grid recomputed",
        "grid_cells": len(_grid_cache["geojson"]["features"]) if _grid_cache["geojson"] else 0,
    }


# ─── Init files ────────────────────────────────────────────────────────
# These are created by the file structure, but we need __init__.py files
