import { AQI_SCALE } from "../aqiUtils";

/**
 * AQI Legend — Color scale overlay on the map.
 */
export default function AQILegend() {
  return (
    <div className="legend" id="aqi-legend">
      <div className="legend__title">PM2.5 Prediction (India NAQI)</div>
      <div className="legend__scale">
        {AQI_SCALE.map((seg) => (
          <div
            key={seg.label}
            className="legend__segment"
            style={{ background: seg.color }}
            title={`${seg.label}: AQI ${seg.range}`}
          />
        ))}
      </div>
      <div className="legend__labels">
        <span>Good</span>
        <span>Moderate</span>
        <span>Poor</span>
        <span>Severe</span>
      </div>
    </div>
  );
}
