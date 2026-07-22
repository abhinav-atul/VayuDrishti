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
      {/* Background Map Layer */}
      <div className="app__map">
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
      </div>

      {/* Top Navbar */}
      <div className="top-nav">
        <div className="top-nav__brand">
          <span className="top-nav__logo">🌬️</span>
          <span className="top-nav__title">VayuDrishti</span>
        </div>
        <div className="top-nav__links">
          <span className="top-nav__link top-nav__link--active">Dashboard</span>
          <span className="top-nav__link">Monitoring</span>
          <span className="top-nav__link">Forecasting</span>
        </div>
        <div className="top-nav__right">
          <div className="top-nav__search">
            <span>🔍</span>
            <input type="text" placeholder="Search location..." />
          </div>
          <div className="top-nav__profile">AA</div>
        </div>
      </div>

      {/* Floating Sidebar Panel */}
      <div className="app__sidebar">
        <Sidebar
          stations={stations}
          selectedPoint={selectedPoint}
          metrics={metrics}
          onStationClick={handleStationClick}
        />
      </div>

      {/* Map Info Badges (moved to top right under navbar) */}
      <div className="map-info" style={{ top: '90px' }}>
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

      {/* AQI Legend */}
      <AQILegend />

      {/* Chat Toggle & Panel */}
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
  );
}
