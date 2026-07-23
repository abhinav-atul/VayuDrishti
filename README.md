<div align="center">
  <h1>🌬️ VayuDrishti</h1>
  <p><strong>Hyperlocal Air Quality Intelligence via Spatial Machine Learning</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/Frontend-React%20%7C%20MapLibre-61DAFB?style=flat-square&logo=react" alt="Frontend" />
    <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" alt="Backend" />
    <img src="https://img.shields.io/badge/ML-XGBoost%20%7C%20Pandas-blue?style=flat-square&logo=pandas" alt="ML" />
    <img src="https://img.shields.io/badge/Satellite-NASA%20VIIRS%20%7C%20Sentinel--5P-0B3D91?style=flat-square" alt="Satellite" />
  </p>
</div>

<br/>

> **The Problem:** Delhi, a megacity of over 30 million people, relies on just ~40 ground monitoring stations to report Air Quality (AQI). If you don't live immediately next to a station, your local air quality is effectively a blind spot.

> **Our Solution:** **VayuDrishti** fills the gaps. By fusing ground station telemetry with orbital satellite data, fire hotspots, and urban geography, our Machine Learning engine generates a continuous, hyperlocal PM2.5 heatmap across the entire city. Click any street corner in Delhi, and VayuDrishti will accurately predict the exact air quality you are breathing.

---

## 🌟 Key Features

1. **Hyperlocal Continuous Heatmap**: Real-time rendering of a 1km² resolution spatial grid mapping PM2.5 across all of Delhi—covering both monitored and unmonitored zones.
2. **Spatial Machine Learning**: An XGBoost Regressor trained on 26 distinct spatial features to accurately interpolate pollution levels between sparse ground stations.
3. **Multi-Modal Data Fusion**: Automatically aggregates and engineers features from ground sensors (WAQI), weather (OpenWeatherMap), road density (OSM heuristics), and satellites (Sentinel-5P, NASA VIIRS).
4. **Interactive Glassmorphism Dashboard**: A stunning, hardware-accelerated WebGL map interface built with MapLibre GL JS and modern React.
5. **AI Health Advisory**: An integrated LLM Agent (powered by Gemini Flash) that provides hyper-personalized health advisories based on the precise AQI prediction at your clicked location.

---

## 🧠 Machine Learning Architecture

VayuDrishti moves beyond simple interpolation (like IDW or Kriging) by using a **Gradient Boosted Decision Tree (XGBoost Regressor)** to capture non-linear relationships between pollution and urban infrastructure.

### Feature Engineering (26 Spatial Features)
For every 1km² grid cell, the model computes:
- **Baseline Proximity**: Inverse Distance Weighting (IDW) of PM2.5 from the 3 nearest ground stations.
- **Urban Topology**: Distance to the city center, distance to nearest major highway, and road density density heuristic.
- **Orbital Telemetry**: Sentinel-5P satellite measurements for tropospheric NO₂ and SO₂ column density.
- **Meteorology**: Temperature, relative humidity, wind speed, wind direction, and surface pressure.
- **Stubble Burning / Industrial**: Distance to the nearest active VIIRS satellite fire hotspot, fire count within a 10km radius, and industrial proximity flags.

### Model Validation (LOSO)
We validate the model's accuracy using **Leave-One-Station-Out (LOSO) Cross-Validation**. 
The model iterativly holds out one ground station, trains on the rest, and attempts to predict the pollution at the hidden station. This proves the model's ability to accurately infer pollution levels at geographic coordinates it has never seen before.

---

## 🛠️ Data Engineering Pipelines

VayuDrishti's backend operates complex spatial pipelines on-the-fly:
- **Ground Truth**: Pulls live station data from the **WAQI API**.
- **Meteorology**: Integrates live conditions from **OpenWeatherMap**.
- **Fire Hotspots**: Fetches active fire anomalies detected by NASA's Suomi NPP (VIIRS) sensor via the **NASA FIRMS API**.
- **Trace Gases**: Authenticates via a Google Service Account to execute cloud queries on **Google Earth Engine (GEE)**, extracting mean raster values of Sentinel-5P NO₂ and SO₂.

---

## 💻 Technical Stack

### Frontend
- **Framework**: React 19 + Vite
- **Styling**: Vanilla CSS (Modern Glassmorphism Design System)
- **Mapping Engine**: MapLibre GL JS (WebGL vector tiles)
- **Data Fetching**: Native Fetch API with asynchronous loading states.

### Backend
- **Framework**: FastAPI (Python)
- **ML / Data Science**: XGBoost, Scikit-Learn, Pandas, NumPy
- **Spatial Processing**: GeoPandas, Shapely, PyProj, Google Earth Engine API
- **AI Integration**: OpenRouter SDK (routing to Google Gemini Flash)

---

## 🚀 Quick Start & Installation

### Prerequisites
- Node.js (v18+)
- Python (3.10+)
- Free API Keys (See below)

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment Variables
# Copy the example file and add your keys. 
# NOTE: The app will run in "Demo Mode" with mock data if keys are missing!
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
# The dashboard will open at http://localhost:5173
```

### 3. Model Training

When both servers are running, the application will automatically train the ML model upon the first dashboard load. Alternatively, you can trigger a retrain manually via the REST API:

```bash
curl -X POST http://localhost:8000/api/model/train
```

---

## 🔑 Required API Keys

All services used by VayuDrishti offer generous free tiers. Add these to your `.env` file in the backend.

| Service | URL | Purpose |
|---|---|---|
| **WAQI** | [Register](https://aqicn.org/data-platform/token/) | Real-time AQI stations |
| **OpenWeatherMap** | [Register](https://openweathermap.org/api) | Real-time Weather data |
| **NASA FIRMS** | [Register](https://firms.modaps.eosdis.nasa.gov/api/map_key) | VIIRS Fire hotspot detection |
| **OpenRouter** | [Register](https://openrouter.ai/keys) | LLM Chatbot Advisory |
| **Google Earth Engine** | [Register](https://earthengine.google.com/) | Sentinel-5P Satellite features |

*(Note: For GEE, you will also need to place your JSON Service Account Key inside the backend folder and update the path in `.env`)*

---

<div align="center">
  <p>Built for the <strong>ET AI Hackathon 2026</strong></p>
  <p><em>Stream 5: Urban Air Quality Intelligence</em></p>
</div>
