/**
 * AQI utility functions
 * India National AQI standard color mapping and category logic.
 */

export function aqiColor(aqi) {
  if (aqi <= 50) return "#10b981";   // Good
  if (aqi <= 100) return "#84cc16";  // Satisfactory
  if (aqi <= 200) return "#eab308";  // Moderate
  if (aqi <= 300) return "#f97316";  // Poor
  if (aqi <= 400) return "#ef4444";  // Very Poor
  return "#991b1b";                   // Severe
}

export function aqiCategory(aqi) {
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

export function aqiBadgeClass(aqi) {
  if (aqi <= 50) return "aqi-badge--good";
  if (aqi <= 100) return "aqi-badge--satisfactory";
  if (aqi <= 200) return "aqi-badge--moderate";
  if (aqi <= 300) return "aqi-badge--poor";
  if (aqi <= 400) return "aqi-badge--very-poor";
  return "aqi-badge--severe";
}

export function pm25ToAqi(pm25) {
  const breakpoints = [
    [0, 30, 0, 50],
    [31, 60, 51, 100],
    [61, 90, 101, 200],
    [91, 120, 201, 300],
    [121, 250, 301, 400],
    [251, 500, 401, 500],
  ];
  for (const [bpLo, bpHi, aqiLo, aqiHi] of breakpoints) {
    if (pm25 <= bpHi) {
      return Math.round(aqiLo + ((pm25 - bpLo) * (aqiHi - aqiLo)) / (bpHi - bpLo));
    }
  }
  return 500;
}

/** Map AQI to a CSS-friendly background with low opacity */
export function aqiBgColor(aqi, opacity = 0.15) {
  const hex = aqiColor(aqi);
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

/** AQI scale segments for the legend */
export const AQI_SCALE = [
  { label: "Good", range: "0-50", color: "#10b981" },
  { label: "Satisfactory", range: "51-100", color: "#84cc16" },
  { label: "Moderate", range: "101-200", color: "#eab308" },
  { label: "Poor", range: "201-300", color: "#f97316" },
  { label: "Very Poor", range: "301-400", color: "#ef4444" },
  { label: "Severe", range: "401-500", color: "#991b1b" },
];
