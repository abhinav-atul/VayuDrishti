import { useState, useMemo } from "react";
import { aqiColor, aqiBadgeClass, aqiCategory } from "../aqiUtils";

/**
 * Sidebar — Station list, model stats, selected point details, feature importance.
 * Glassmorphism design with frosted glass cards and soft pastel tints.
 */
export default function Sidebar({ stations, selectedPoint, metrics, onStationClick, tab }) {

  // Sort stations by AQI (worst first)
  const sortedStations = useMemo(() => {
    return [...(stations || [])]
      .filter((s) => s.aqi && s.aqi > 0)
      .sort((a, b) => (b.aqi || 0) - (a.aqi || 0));
  }, [stations]);

  // Compute city-wide stats
  const cityStats = useMemo(() => {
    const valid = sortedStations.filter((s) => s.aqi > 0);
    if (!valid.length) return null;
    const avgAqi = Math.round(valid.reduce((sum, s) => sum + s.aqi, 0) / valid.length);
    const avgPm25 = Math.round(
      valid.filter((s) => s.pm25).reduce((sum, s) => sum + s.pm25, 0) /
      valid.filter((s) => s.pm25).length || 0
    );
    return {
      avgAqi,
      avgPm25,
      worst: valid[0],
      best: valid[valid.length - 1],
      total: valid.length,
    };
  }, [sortedStations]);

  const featureImportance = metrics?.feature_importance || [];
  const validation = metrics?.validation || {};
  const maxImportance = featureImportance.length > 0
    ? Math.max(...featureImportance.map((f) => f.importance))
    : 1;

  return (
    <>
      <div className="sidebar-content">
        {/* ─── OVERVIEW TAB ─── */}
        {tab === "overview" && (
          <>
            {/* Selected Point */}
            {selectedPoint && (
              <div className="metric-card metric-card--mint" style={{ borderColor: aqiColor(selectedPoint.predicted_aqi) + "30" }}>
                <div className="metric-card__label">
                  {selectedPoint.isStation ? "📍 Station Reading" : "🎯 ML Estimate at Click"}
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                  <span
                    className="metric-card__value"
                    style={{ color: aqiColor(selectedPoint.predicted_aqi) }}
                  >
                    {selectedPoint.predicted_aqi}
                  </span>
                  <span className={`aqi-badge ${aqiBadgeClass(selectedPoint.predicted_aqi)}`}>
                    {selectedPoint.aqi_category}
                  </span>
                </div>
                <div className="metric-card__detail">
                  PM2.5: {selectedPoint.predicted_pm25} µg/m³
                  {selectedPoint.confidence && ` • Confidence: ${selectedPoint.confidence}`}
                </div>
                {selectedPoint.nearest_station_name && (
                  <div className="metric-card__detail">
                    Nearest: {selectedPoint.nearest_station_name?.replace(", Delhi", "")}
                    {selectedPoint.nearest_station_dist_km > 0 &&
                      ` (${selectedPoint.nearest_station_dist_km} km)`}
                  </div>
                )}
                {selectedPoint.health_advisory && (
                  <div className="metric-card__detail" style={{ marginTop: "8px", fontStyle: "italic" }}>
                    {selectedPoint.health_advisory}
                  </div>
                )}
              </div>
            )}

            {!selectedPoint && (
              <div className="metric-card metric-card--lavender">
                <div className="metric-card__label">👆 Click anywhere on the map</div>
                <div className="metric-card__detail" style={{ marginTop: "4px" }}>
                  Get an ML-powered PM2.5 estimate at any point in Delhi — even between monitoring stations.
                </div>
              </div>
            )}

            {/* City-Wide Stats */}
            {cityStats && (
              <>
                <div className="section-header">📊 Delhi Overview</div>
                <div className="metric-grid">
                  <div className="metric-card metric-card--mint">
                    <div className="metric-card__label">Avg AQI</div>
                    <div className="metric-card__value" style={{ color: aqiColor(cityStats.avgAqi) }}>
                      {cityStats.avgAqi}
                    </div>
                    <div className="metric-card__detail">{aqiCategory(cityStats.avgAqi)}</div>
                  </div>
                  <div className="metric-card metric-card--lavender">
                    <div className="metric-card__label">Avg PM2.5</div>
                    <div className="metric-card__value" style={{ color: "#4a9e8e" }}>
                      {cityStats.avgPm25}
                    </div>
                    <div className="metric-card__detail">µg/m³</div>
                  </div>
                  <div className="metric-card metric-card--blush">
                    <div className="metric-card__label">Worst</div>
                    <div className="metric-card__value" style={{ color: aqiColor(cityStats.worst.aqi), fontSize: "1.2rem" }}>
                      {cityStats.worst.aqi}
                    </div>
                    <div className="metric-card__detail" style={{ fontSize: "0.65rem" }}>
                      {cityStats.worst.name?.replace(", Delhi", "")}
                    </div>
                  </div>
                  <div className="metric-card metric-card--mint">
                    <div className="metric-card__label">Best</div>
                    <div className="metric-card__value" style={{ color: aqiColor(cityStats.best.aqi), fontSize: "1.2rem" }}>
                      {cityStats.best.aqi}
                    </div>
                    <div className="metric-card__detail" style={{ fontSize: "0.65rem" }}>
                      {cityStats.best.name?.replace(", Delhi", "")}
                    </div>
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-card__label">Active Monitoring</div>
                  <div className="metric-card__detail">
                    {cityStats.total} stations reporting • ~{Math.round(1484 / cityStats.total)} km² per station
                  </div>
                  <div className="metric-card__detail" style={{ color: "#4a9e8e", fontWeight: 600 }}>
                    VayuDrishti fills the gaps with spatial ML ↗
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* ─── STATIONS TAB ─── */}
        {tab === "stations" && (
          <>
            <div className="section-header">
              📡 Ground Truth Stations ({sortedStations.length})
            </div>
            <div className="station-list">
              {sortedStations.map((s) => (
                <div
                  key={s.station_id}
                  className="station-item"
                  onClick={() => onStationClick?.(s)}
                >
                  <span className="station-item__name">
                    {s.name?.replace(", Delhi", "")}
                  </span>
                  <span
                    className="station-item__aqi"
                    style={{
                      background: aqiColor(s.aqi) + "18",
                      color: aqiColor(s.aqi),
                    }}
                  >
                    {s.aqi}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ─── MODEL TAB ─── */}
        {tab === "model" && (
          <>
            <div className="section-header">🧪 Model Validation (LOSO)</div>

            {validation.r2_mean !== undefined ? (
              <>
                <div className="metric-grid">
                  <div className="metric-card metric-card--mint">
                    <div className="metric-card__label">R² Score</div>
                    <div className="metric-card__value" style={{ color: validation.r2_mean > 0.7 ? "var(--aqi-good)" : validation.r2_mean > 0.5 ? "var(--aqi-moderate)" : "var(--aqi-poor)" }}>
                      {validation.r2_mean.toFixed(3)}
                    </div>
                    <div className="metric-card__detail">±{validation.r2_std?.toFixed(3) || "0"}</div>
                  </div>
                  <div className="metric-card metric-card--lavender">
                    <div className="metric-card__label">RMSE</div>
                    <div className="metric-card__value" style={{ color: "#4a9e8e" }}>
                      {validation.rmse_mean?.toFixed(1)}
                    </div>
                    <div className="metric-card__detail">µg/m³</div>
                  </div>
                  <div className="metric-card metric-card--blush">
                    <div className="metric-card__label">MAE</div>
                    <div className="metric-card__value" style={{ color: "#4a9e8e" }}>
                      {validation.mae_mean?.toFixed(1)}
                    </div>
                    <div className="metric-card__detail">µg/m³</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-card__label">Stations</div>
                    <div className="metric-card__value" style={{ color: "var(--text-primary)" }}>
                      {validation.n_stations || 0}
                    </div>
                    <div className="metric-card__detail">held out</div>
                  </div>
                </div>

                <div className="metric-card metric-card--lavender">
                  <div className="metric-card__detail">
                    <strong>Leave-One-Station-Out:</strong> Each station was held out while the model trained on the remaining stations. The R² score shows prediction accuracy at locations the model has never seen.
                  </div>
                </div>
              </>
            ) : (
              <div className="metric-card metric-card--blush">
                <div className="metric-card__detail">
                  No validation results yet. Train the model via the API to generate LOSO metrics.
                </div>
              </div>
            )}

            {/* Feature Importance */}
            {featureImportance.length > 0 && (
              <>
                <div className="section-header" style={{ marginTop: "8px" }}>
                  📊 Feature Importance
                </div>
                {featureImportance.slice(0, 10).map((f) => (
                  <div key={f.feature} className="importance-bar">
                    <span className="importance-bar__label">
                      {f.feature.replace(/_/g, " ")}
                    </span>
                    <div className="importance-bar__track">
                      <div
                        className="importance-bar__fill"
                        style={{ width: `${(f.importance / maxImportance) * 100}%` }}
                      />
                    </div>
                    <span className="importance-bar__value">
                      {(f.importance * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </>
            )}

            {/* Model Info */}
            <div className="metric-card metric-card--mint" style={{ marginTop: "4px" }}>
              <div className="metric-card__label">Model Architecture</div>
              <div className="metric-card__detail">
                XGBoost Regressor • 26 features • Spatial ML fusion of ground stations + Sentinel-5P satellite + VIIRS fire + weather + land use
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
