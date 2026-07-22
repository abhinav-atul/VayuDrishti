# VayuDrishti — Hyperlocal Air Quality Intelligence

> **Delhi has ~40 monitoring stations for 20 million people.** VayuDrishti uses spatial ML to estimate PM2.5 at any point in the city by fusing ground stations, satellite data, fire hotspots, weather, and land use features.

## Quick Start

### 1. Backend (Python)

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Copy .env.example → .env and add your API keys
# (App works with demo data even without real keys)

.\venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend (React)

```bash
cd frontend
npm install
npm run dev
# → opens at http://localhost:5173
```

### 3. Train the ML Model

After both servers are running, the model auto-trains on first request.
Or trigger manually:

```bash
curl -X POST http://localhost:8000/api/model/train
```

## API Keys (All Free)

| Service | URL | Purpose |
|---|---|---|
| WAQI | https://aqicn.org/data-platform/token/ | Real-time AQI stations |
| OpenWeatherMap | https://openweathermap.org/api | Weather data |
| NASA FIRMS | https://firms.modaps.eosdis.nasa.gov/api/map_key | Fire hotspot detection |
| OpenAQ | https://explore.openaq.org/register | Historical AQI data |
| OpenRouter | https://openrouter.ai/keys | LLM chatbot |
| Google Earth Engine | https://earthengine.google.com/ | Satellite features |

## Architecture

```
Ground Stations (WAQI) ──┐
Satellite (Sentinel-5P) ──┤
Fire Hotspots (VIIRS) ────┼──→ Feature Matrix ──→ XGBoost ──→ 1km Grid PM2.5 Map
Weather (OpenWeatherMap) ──┤    (26 features       Model      (2,400+ cells)
Land Use (OSM heuristics) ┘     per cell)
```

## Tech Stack

- **Frontend**: React 19, MapLibre GL JS, Recharts
- **Backend**: FastAPI, XGBoost, Pandas, GeoPandas
- **Data**: WAQI, OpenWeatherMap, NASA VIIRS FIRMS, Sentinel-5P
- **LLM**: OpenRouter (Gemini Flash)

## Team

ET AI Hackathon 2026 — Stream 5: Urban Air Quality Intelligence
