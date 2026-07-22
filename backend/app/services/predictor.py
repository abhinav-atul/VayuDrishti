"""
Predictor — XGBoost model for hyperlocal PM2.5 estimation.

Handles model training, LOSO cross-validation, and inference.
The model learns to predict PM2.5 at any location given the feature vector
assembled by the grid engine.
"""

import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor
import joblib

from app.config import settings
from app.services.grid_engine import FEATURE_COLUMNS, haversine_km
from app.schemas import StationReading, GridCell, FireHotspot

_model = None


def _pm25_to_aqi(pm25: float) -> int:
    """Convert PM2.5 to Indian NAQI."""
    breakpoints = [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 500, 401, 500),
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if pm25 <= bp_hi:
            return round(aqi_lo + (pm25 - bp_lo) * (aqi_hi - aqi_lo) / (bp_hi - bp_lo))
    return 500


def _aqi_category(aqi: int) -> str:
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    else: return "Severe"


def _confidence_level(nearest_dist_km: float) -> str:
    """Estimate confidence based on proximity to nearest station."""
    if nearest_dist_km < 3:
        return "high"
    elif nearest_dist_km < 8:
        return "medium"
    else:
        return "low"


def load_model():
    """Load the trained XGBoost model from disk."""
    global _model
    model_path = settings.MODEL_PATH
    if model_path.exists():
        _model = joblib.load(model_path)
        print(f"Loaded model from {model_path}")
    else:
        print("No trained model found. Using IDW fallback.")
        _model = None


def train_model(training_df: pd.DataFrame) -> XGBRegressor:
    """Train XGBoost model on station data.
    
    training_df must have FEATURE_COLUMNS + 'pm25' (target).
    Each row represents a station observation with features computed
    as if the model were predicting at that station's location.
    """
    features = training_df[FEATURE_COLUMNS].copy()
    target = training_df["pm25"]

    model = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(features, target)

    # Save model
    settings.ML_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, settings.MODEL_PATH)
    print(f"Model saved to {settings.MODEL_PATH}")

    # Save feature importance
    importance = []
    for feat, imp in zip(FEATURE_COLUMNS, model.feature_importances_):
        importance.append({"feature": feat, "importance": round(float(imp), 4)})
    importance.sort(key=lambda x: x["importance"], reverse=True)

    with open(settings.SHAP_PATH, "w") as f:
        json.dump(importance, f, indent=2)

    global _model
    _model = model
    return model


def loso_cross_validate(station_observations: pd.DataFrame) -> dict:
    """Leave-One-Station-Out cross-validation.
    
    For each station:
    1. Train on all OTHER stations' observations
    2. Predict on the held-out station
    3. Record R², RMSE, MAE
    
    This proves the model can predict at locations it has never seen.
    """
    station_ids = station_observations["station_id"].unique()
    results = []

    for held_out_id in station_ids:
        train_mask = station_observations["station_id"] != held_out_id
        test_mask = station_observations["station_id"] == held_out_id

        train_df = station_observations[train_mask]
        test_df = station_observations[test_mask]

        if len(train_df) < 5 or len(test_df) < 1:
            continue

        model = XGBRegressor(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
        )

        features_train = train_df[FEATURE_COLUMNS]
        target_train = train_df["pm25"]
        features_test = test_df[FEATURE_COLUMNS]
        target_test = test_df["pm25"]

        model.fit(features_train, target_train)
        predictions = model.predict(features_test)

        # Handle edge case: single test sample
        if len(target_test) == 1:
            r2 = 0.0  # R² undefined for single sample
            rmse = float(np.sqrt((target_test.iloc[0] - predictions[0]) ** 2))
            mae = float(abs(target_test.iloc[0] - predictions[0]))
        else:
            r2 = float(r2_score(target_test, predictions))
            rmse = float(np.sqrt(mean_squared_error(target_test, predictions)))
            mae = float(mean_absolute_error(target_test, predictions))

        station_name = test_df.iloc[0].get("station_name", held_out_id)
        results.append({
            "station_id": str(held_out_id),
            "station_name": str(station_name),
            "r2": round(r2, 4),
            "rmse": round(rmse, 2),
            "mae": round(mae, 2),
            "n_test": len(test_df),
            "actual_mean": round(float(target_test.mean()), 1),
            "predicted_mean": round(float(predictions.mean()), 1),
        })

    # Aggregate metrics
    r2_vals = [r["r2"] for r in results if r["r2"] != 0.0]  # Exclude single-sample
    rmse_vals = [r["rmse"] for r in results]
    mae_vals = [r["mae"] for r in results]

    validation = {
        "r2_mean": round(float(np.mean(r2_vals)) if r2_vals else 0.0, 4),
        "r2_std": round(float(np.std(r2_vals)) if r2_vals else 0.0, 4),
        "rmse_mean": round(float(np.mean(rmse_vals)), 2),
        "rmse_std": round(float(np.std(rmse_vals)), 2),
        "mae_mean": round(float(np.mean(mae_vals)), 2),
        "mae_std": round(float(np.std(mae_vals)), 2),
        "n_stations": len(results),
        "per_station": results,
    }

    # Save validation results
    settings.ML_DIR.mkdir(parents=True, exist_ok=True)
    with open(settings.VALIDATION_PATH, "w") as f:
        json.dump(validation, f, indent=2)

    return validation


def predict_grid(feature_df: pd.DataFrame) -> list[GridCell]:
    """Run inference on the full grid.
    
    feature_df: DataFrame from grid_engine.build_feature_matrix()
    Returns list of GridCell with predictions.
    """
    if _model is not None:
        features = feature_df[FEATURE_COLUMNS]
        predictions = _model.predict(features)
        # Clamp to reasonable range
        predictions = np.clip(predictions, 0, 500)
    else:
        # Fallback: use IDW interpolation directly
        predictions = feature_df["idw_pm25"].values

    cells = []
    for i, row in feature_df.iterrows():
        pm25 = float(predictions[i] if isinstance(i, int) else predictions[list(feature_df.index).index(i)])
        aqi = _pm25_to_aqi(pm25)

        cells.append(GridCell(
            row=int(row["row"]),
            col=int(row["col"]),
            lat=float(row["lat"]),
            lng=float(row["lng"]),
            predicted_pm25=round(pm25, 1),
            predicted_aqi=aqi,
            aqi_category=_aqi_category(aqi),
            confidence=_confidence_level(float(row["nearest_station_dist_km"])),
            nearest_station_dist_km=float(row["nearest_station_dist_km"]),
        ))

    return cells


def predict_point(
    lat: float,
    lng: float,
    feature_df: pd.DataFrame,
    stations: list[StationReading],
) -> dict:
    """Predict AQI at a specific arbitrary point.
    
    Finds the nearest grid cell and returns its prediction with metadata.
    """
    # Find nearest grid cell
    min_dist = float("inf")
    nearest_idx = 0
    for i, row in feature_df.iterrows():
        d = haversine_km(lat, lng, row["lat"], row["lng"])
        if d < min_dist:
            min_dist = d
            nearest_idx = i

    row = feature_df.loc[nearest_idx]

    if _model is not None:
        features = row[FEATURE_COLUMNS].values.reshape(1, -1)
        pm25 = float(_model.predict(features)[0])
        pm25 = max(0, min(500, pm25))
    else:
        pm25 = float(row["idw_pm25"])

    aqi = _pm25_to_aqi(pm25)

    return {
        "lat": lat,
        "lng": lng,
        "predicted_pm25": round(pm25, 1),
        "predicted_aqi": aqi,
        "aqi_category": _aqi_category(aqi),
        "aqi_color": _aqi_color(aqi),
        "confidence": _confidence_level(float(row["nearest_station_dist_km"])),
        "nearest_station_name": str(row.get("nearest_station_name", "Unknown")),
        "nearest_station_dist_km": round(float(row["nearest_station_dist_km"]), 2),
        "health_advisory": _health_advisory(aqi),
    }


def _aqi_color(aqi: int) -> str:
    if aqi <= 50: return "#10b981"
    elif aqi <= 100: return "#84cc16"
    elif aqi <= 200: return "#eab308"
    elif aqi <= 300: return "#f97316"
    elif aqi <= 400: return "#ef4444"
    else: return "#991b1b"


def _health_advisory(aqi: int) -> str:
    if aqi <= 50:
        return "Air quality is satisfactory. Ideal for outdoor activities."
    elif aqi <= 100:
        return "Acceptable air quality. Sensitive individuals should limit prolonged outdoor exertion."
    elif aqi <= 200:
        return "May cause breathing discomfort. Minimize outdoor activities."
    elif aqi <= 300:
        return "Unhealthy. Avoid outdoor activities, especially for children and elderly."
    elif aqi <= 400:
        return "Very unhealthy. Avoid all outdoor physical activities."
    else:
        return "Severe. Stay indoors. Use air purifier if available."


def generate_training_data(stations: list[StationReading], fires: list[FireHotspot], weather: dict, satellite_data: dict | None = None) -> pd.DataFrame:
    """Generate training data from current station readings.
    
    For each station, compute features AS IF predicting at that location,
    but EXCLUDING that station from the feature computation (to prevent data leakage).
    The station's own PM2.5 reading is the training label.
    """
    from app.services.grid_engine import (
        compute_station_features,
        compute_fire_features,
        compute_spatial_features,
        compute_temporal_features,
    )
    from app.services.satellite import get_satellite_value, _get_baseline_data

    temporal = compute_temporal_features()
    sat_data = satellite_data if satellite_data else _get_baseline_data()
    rows = []

    for target_station in stations:
        if target_station.pm25 is None or target_station.pm25 <= 0:
            continue

        # Exclude this station when computing station features (prevent leakage!)
        other_stations = [s for s in stations if s.station_id != target_station.station_id]

        station_feats = compute_station_features(
            target_station.lat, target_station.lng, other_stations
        )
        fire_feats = compute_fire_features(
            target_station.lat, target_station.lng, fires
        )
        spatial_feats = compute_spatial_features(
            target_station.lat, target_station.lng
        )
        sat_feats = get_satellite_value(
            target_station.lat, target_station.lng, sat_data
        )

        row = {
            "station_id": target_station.station_id,
            "station_name": target_station.name,
            "pm25": target_station.pm25,  # Label
            "lat": target_station.lat,
            "lng": target_station.lng,
            **station_feats,
            **fire_feats,
            **spatial_feats,
            **sat_feats,
            "temperature": weather.get("temperature", 32),
            "humidity": weather.get("humidity", 55),
            "wind_speed": weather.get("wind_speed", 2.5),
            "wind_direction": weather.get("wind_direction", 240),
            "pressure": weather.get("pressure", 1012),
            **temporal,
        }
        rows.append(row)

    return pd.DataFrame(rows)
