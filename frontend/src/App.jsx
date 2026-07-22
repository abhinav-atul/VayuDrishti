import { useState, useEffect, useCallback } from "react";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import AQILegend from "./components/AQILegend";
import { fetchGrid, fetchStations, fetchFires, fetchModelMetrics } from "./api";

export default function App() {
  const [gridData, setGridData] = useState(null);
  const [stations, setStations] = useState([]);
  const [fires, setFires] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load all data on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [grid, stns, frs, mets] = await Promise.all([
          fetchGrid().catch(() => null),
          fetchStations().catch(() => []),
          fetchFires().catch(() => []),
          fetchModelMetrics().catch(() => null),
        ]);
        setGridData(grid);
        setStations(stns);
        setFires(frs);
        setMetrics(mets);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleMapClick = useCallback((pointData) => {
    setSelectedPoint(pointData);
  }, []);

  const handleStationClick = useCallback((station) => {
    setSelectedPoint({
      lat: station.lat,
      lng: station.lng,
      predicted_pm25: station.pm25 || 0,
      predicted_aqi: station.aqi || 0,
      aqi_category: station.aqi <= 50 ? "Good" : station.aqi <= 100 ? "Satisfactory" : station.aqi <= 200 ? "Moderate" : station.aqi <= 300 ? "Poor" : station.aqi <= 400 ? "Very Poor" : "Severe",
      confidence: "high",
      nearest_station_name: station.name,
      nearest_station_dist_km: 0,
      isStation: true,
    });
  }, []);

  return (
    <div className="app">
      <div className="app__map">
        {/* Logo Header */}
        <div className="header">
          <span className="header__icon">🌬️</span>
          <div>
            <div className="header__title">VayuDrishti</div>
            <div className="header__subtitle">Hyperlocal Air Quality Intelligence</div>
          </div>
        </div>

        {/* Map Info Badges */}
        <div className="map-info">
          <div className="map-info__badge">
            <span className="map-info__dot" style={{ background: "#10b981" }} />
            {stations.length} Stations
          </div>
          <div className="map-info__badge">
            <span className="map-info__dot" style={{ background: "#f97316" }} />
            {fires.length} Fire Hotspots
          </div>
          {gridData && (
            <div className="map-info__badge">
              <span className="map-info__dot" style={{ background: "#22d3ee" }} />
              {gridData.features?.length || 0} Grid Cells
            </div>
          )}
        </div>

        {/* Main Map */}
        {loading ? (
          <div className="loading">
            <div className="loading__spinner" />
            <div className="loading__text">Loading air quality data...</div>
          </div>
        ) : (
          <MapView
            gridData={gridData}
            stations={stations}
            fires={fires}
            selectedPoint={selectedPoint}
            onMapClick={handleMapClick}
          />
        )}

        {/* AQI Legend */}
        <AQILegend />

        {/* Chat Toggle */}
        <button
          className="chat-toggle"
          onClick={() => setChatOpen(!chatOpen)}
          title="Air Quality Advisory"
          id="chat-toggle-btn"
        >
          {chatOpen ? "✕" : "💬"}
        </button>

        {/* Chat Panel */}
        {chatOpen && (
          <ChatPanel
            selectedPoint={selectedPoint}
            onClose={() => setChatOpen(false)}
          />
        )}
      </div>

      {/* Sidebar */}
      <div className="app__sidebar">
        <Sidebar
          stations={stations}
          selectedPoint={selectedPoint}
          metrics={metrics}
          onStationClick={handleStationClick}
        />
      </div>
    </div>
  );
}
