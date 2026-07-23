import { useState } from "react";
import { AQI_SCALE } from "../aqiUtils";

/**
 * AQI Legend — Compact toggleable color scale icon on the bottom right.
 */
export default function AQILegend() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="legend-wrapper">
      {isOpen && (
        <div className="legend" id="aqi-legend">
          <div className="legend__title">PM2.5 Scale (NAQI)</div>
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
            <span>Mod</span>
            <span>Poor</span>
            <span>Sev</span>
          </div>
        </div>
      )}
      <button
        className="legend-toggle"
        onClick={() => setIsOpen(!isOpen)}
        title="Toggle AQI Color Legend"
      >
        <span className="legend-toggle__gradient" />
        <span>AQI Scale</span>
      </button>
    </div>
  );
}
