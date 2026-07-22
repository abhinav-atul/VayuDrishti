"""
VayuDrishti Configuration
Loads API keys and settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend root
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


class Settings:
    """Application settings loaded from environment."""

    # API Keys
    WAQI_TOKEN: str = os.getenv("WAQI_TOKEN", "")
    OWM_API_KEY: str = os.getenv("OWM_API_KEY", "")
    FIRMS_MAP_KEY: str = os.getenv("FIRMS_MAP_KEY", "")
    OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEE_API_KEY: str = os.getenv("GEE_API_KEY", "")
    GEE_SERVICE_ACCOUNT_JSON: str = os.getenv("GEE_SERVICE_ACCOUNT_JSON", "")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",")

    # Delhi bounding box
    DELHI_BBOX = {
        "lat_min": 28.40,
        "lat_max": 28.88,
        "lng_min": 76.84,
        "lng_max": 77.35,
    }

    # Grid resolution in degrees (~1.1km at Delhi's latitude)
    GRID_RESOLUTION: float = 0.01

    # Data paths
    DATA_DIR: Path = Path(__file__).resolve().parent / "data"
    ML_DIR: Path = Path(__file__).resolve().parent / "ml"
    MODEL_PATH: Path = ML_DIR / "model.joblib"
    VALIDATION_PATH: Path = ML_DIR / "validation_results.json"
    SHAP_PATH: Path = ML_DIR / "shap_importance.json"

    # Cache TTLs (seconds)
    WAQI_CACHE_TTL: int = 900       # 15 minutes
    WEATHER_CACHE_TTL: int = 1800   # 30 minutes
    VIIRS_CACHE_TTL: int = 3600     # 1 hour
    GRID_CACHE_TTL: int = 900       # 15 minutes


settings = Settings()
