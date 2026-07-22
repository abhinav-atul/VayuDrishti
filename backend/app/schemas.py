"""
Pydantic schemas for API request/response models.
"""

from pydantic import BaseModel, Field


class StationReading(BaseModel):
    """A single air quality monitoring station's current reading."""
    station_id: str
    name: str
    lat: float
    lng: float
    aqi: int | None = None
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    so2: float | None = None
    o3: float | None = None
    co: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    timestamp: str | None = None


class GridCell(BaseModel):
    """A single cell in the prediction grid."""
    row: int
    col: int
    lat: float
    lng: float
    predicted_pm25: float
    predicted_aqi: int
    aqi_category: str
    confidence: str  # "high", "medium", "low"
    nearest_station_dist_km: float


class GridResponse(BaseModel):
    """Full grid prediction response."""
    grid: list[GridCell]
    metadata: dict = Field(default_factory=dict)


class PointQuery(BaseModel):
    """Query AQI at an arbitrary point."""
    lat: float = Field(..., ge=28.0, le=29.0)
    lng: float = Field(..., ge=76.0, le=78.0)


class PointEstimate(BaseModel):
    """AQI estimate at a specific point."""
    lat: float
    lng: float
    predicted_pm25: float
    predicted_aqi: int
    aqi_category: str
    aqi_color: str
    confidence: str
    nearest_station_name: str
    nearest_station_dist_km: float
    health_advisory: str


class FireHotspot(BaseModel):
    """A VIIRS-detected fire/thermal anomaly."""
    lat: float
    lng: float
    brightness: float
    frp: float  # Fire Radiative Power
    confidence: str
    acq_date: str
    acq_time: str


class ModelMetrics(BaseModel):
    """LOSO cross-validation results."""
    r2_mean: float
    r2_std: float
    rmse_mean: float
    rmse_std: float
    mae_mean: float
    mae_std: float
    n_stations: int
    per_station: list[dict] = Field(default_factory=list)
    feature_importance: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Chat advisory request."""
    message: str
    lat: float | None = None
    lng: float | None = None
    language: str = "en"  # en, hi, kn, ta


class ChatResponse(BaseModel):
    """Chat advisory response."""
    reply: str
    aqi_context: dict | None = None
    sources: list[str] = Field(default_factory=list)
