import { useRef, useCallback, useState } from "react";
import Map, { Source, Layer, Popup, NavigationControl } from "react-map-gl/maplibre";
import { aqiColor, aqiCategory } from "../aqiUtils";
import { fetchPointEstimate } from "../api";

/**
 * MapView — The core visual component.
 * 
 * Renders:
 * 1. Continuous PM2.5 heatmap grid (the innovation)
 * 2. Ground truth station markers
 * 3. VIIRS fire hotspot markers
 * 4. Click-anywhere point estimate popup
 */
const SATELLITE_STYLE = {
  version: 8,
  sources: {
    "esri-satellite": {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      ],
      tileSize: 256,
      attribution: "Esri, Maxar, Earthstar Geographics"
    }
  },
  layers: [
    {
      id: "esri-satellite-layer",
      type: "raster",
      source: "esri-satellite",
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

export default function MapView({ gridData, stations, fires, selectedPoint, onMapClick, mapTheme }) {
  const mapRef = useRef(null);
  const [popup, setPopup] = useState(null);
  const [loading, setLoading] = useState(false);

  // Handle map click — query the model for that point
  const handleClick = useCallback(async (e) => {
    const { lat, lng } = e.lngLat;
    setLoading(true);

    try {
      const estimate = await fetchPointEstimate(lat, lng);
      const popupData = {
        lat,
        lng: lng,
        ...estimate,
      };
      setPopup(popupData);
      onMapClick?.(popupData);
    } catch (err) {
      // Fallback: find nearest grid cell
      if (gridData?.features) {
        let nearest = null;
        let minDist = Infinity;
        for (const f of gridData.features) {
          const coords = f.geometry.coordinates[0];
          const cLat = (coords[0][1] + coords[2][1]) / 2;
          const cLng = (coords[0][0] + coords[2][0]) / 2;
          const d = Math.hypot(lat - cLat, lng - cLng);
          if (d < minDist) {
            minDist = d;
            nearest = f;
          }
        }
        if (nearest) {
          const p = nearest.properties;
          const popupData = {
            lat,
            lng,
            predicted_pm25: p.pm25,
            predicted_aqi: p.aqi,
            aqi_category: p.category,
            confidence: p.confidence,
          };
          setPopup(popupData);
          onMapClick?.(popupData);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [gridData, onMapClick]);

  // Build station GeoJSON
  const stationGeoJSON = {
    type: "FeatureCollection",
    features: (stations || []).map((s) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [s.lng, s.lat] },
      properties: {
        name: s.name,
        aqi: s.aqi || 0,
        pm25: s.pm25 || 0,
        color: aqiColor(s.aqi || 0),
      },
    })),
  };

  // Build fire GeoJSON
  const fireGeoJSON = {
    type: "FeatureCollection",
    features: (fires || []).map((f) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [f.lng, f.lat] },
      properties: {
        brightness: f.brightness,
        frp: f.frp,
        confidence: f.confidence,
      },
    })),
  };

  // Grid fill color expression based on AQI
  const gridFillColor = [
    "interpolate",
    ["linear"],
    ["get", "pm25"],
    0, "#10b981",    // Good
    30, "#10b981",
    60, "#84cc16",   // Satisfactory
    90, "#eab308",   // Moderate
    120, "#f97316",  // Poor
    250, "#ef4444",  // Very Poor
    400, "#991b1b",  // Severe
  ];

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        longitude: 77.1025,
        latitude: 28.6139,
        zoom: 10.5,
        pitch: 0,
      }}
      style={{ width: "100%", height: "100%" }}
      mapStyle={mapTheme === "satellite" ? SATELLITE_STYLE : "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"}
      onClick={handleClick}
      cursor={loading ? "wait" : "crosshair"}
      attributionControl={false}
    >
      <NavigationControl position="bottom-right" />

      {/* Grid Heatmap Layer — THE core visualization */}
      {gridData && (
        <Source id="grid" type="geojson" data={gridData}>
          <Layer
            id="grid-fill"
            type="fill"
            paint={{
              "fill-color": gridFillColor,
              "fill-opacity": 0.55,
            }}
          />
          <Layer
            id="grid-outline"
            type="line"
            paint={{
              "line-color": "rgba(0, 0, 0, 0.04)",
              "line-width": 0.5,
            }}
          />
        </Source>
      )}

      {/* Station Markers — Ground Truth */}
      <Source id="stations" type="geojson" data={stationGeoJSON}>
        <Layer
          id="station-outer"
          type="circle"
          paint={{
            "circle-radius": 8,
            "circle-color": ["get", "color"],
            "circle-opacity": 0.25,
            "circle-stroke-width": 0,
          }}
        />
        <Layer
          id="station-inner"
          type="circle"
          paint={{
            "circle-radius": 4,
            "circle-color": ["get", "color"],
            "circle-opacity": 0.9,
            "circle-stroke-width": 1.5,
            "circle-stroke-color": "rgba(255, 255, 255, 0.9)",
          }}
        />
        <Layer
          id="station-labels"
          type="symbol"
          layout={{
            "text-field": ["to-string", ["get", "aqi"]],
            "text-size": 10,
            "text-offset": [0, -1.6],
            "text-allow-overlap": false,
          }}
          paint={{
            "text-color": "#1a1a1a",
            "text-halo-color": "rgba(255, 255, 255, 0.9)",
            "text-halo-width": 1.5,
          }}
        />
      </Source>

      {/* Fire Markers — VIIRS Detections */}
      <Source id="fires" type="geojson" data={fireGeoJSON}>
        <Layer
          id="fire-glow"
          type="circle"
          paint={{
            "circle-radius": 14,
            "circle-color": "#ff6b35",
            "circle-opacity": 0.15,
            "circle-blur": 1,
          }}
        />
        <Layer
          id="fire-core"
          type="circle"
          paint={{
            "circle-radius": 5,
            "circle-color": "#ff6b35",
            "circle-opacity": 0.8,
            "circle-stroke-width": 1,
            "circle-stroke-color": "#ffd700",
          }}
        />
        <Layer
          id="fire-labels"
          type="symbol"
          layout={{
            "text-field": "🔥",
            "text-size": 14,
            "text-allow-overlap": true,
          }}
        />
      </Source>

      {/* Selected Point / Click Popup */}
      {popup && (
        <Popup
          longitude={popup.lng}
          latitude={popup.lat}
          anchor="bottom"
          onClose={() => setPopup(null)}
          closeButton={true}
          closeOnClick={false}
          maxWidth="280px"
        >
          <div className="map-popup">
            <div className="map-popup__title" style={{ color: aqiColor(popup.predicted_aqi) }}>
              {popup.aqi_category} Air Quality
            </div>
            <div className="map-popup__row">
              <span className="map-popup__label">PM2.5</span>
              <span className="map-popup__value">{popup.predicted_pm25} µg/m³</span>
            </div>
            <div className="map-popup__row">
              <span className="map-popup__label">AQI</span>
              <span className="map-popup__value" style={{ color: aqiColor(popup.predicted_aqi) }}>
                {popup.predicted_aqi}
              </span>
            </div>
            <div className="map-popup__row">
              <span className="map-popup__label">Confidence</span>
              <span className="map-popup__value">{popup.confidence || "—"}</span>
            </div>
            {popup.nearest_station_name && (
              <div className="map-popup__row">
                <span className="map-popup__label">Nearest Station</span>
                <span className="map-popup__value" style={{ fontSize: "0.7rem" }}>
                  {popup.nearest_station_name?.replace(", Delhi", "")}
                </span>
              </div>
            )}
            {popup.nearest_station_dist_km !== undefined && (
              <div className="map-popup__row">
                <span className="map-popup__label">Station Distance</span>
                <span className="map-popup__value">{popup.nearest_station_dist_km} km</span>
              </div>
            )}
          </div>
        </Popup>
      )}
    </Map>
  );
}
