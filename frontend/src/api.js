const API_BASE = "";

export async function fetchGrid() {
  const res = await fetch(`${API_BASE}/api/grid`);
  if (!res.ok) throw new Error(`Grid fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchPointEstimate(lat, lng) {
  const res = await fetch(
    `${API_BASE}/api/point?lat=${lat}&lng=${lng}`
  );
  if (!res.ok) throw new Error(`Point fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchStations() {
  const res = await fetch(`${API_BASE}/api/stations`);
  if (!res.ok) throw new Error(`Stations fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchFires() {
  const res = await fetch(`${API_BASE}/api/fires`);
  if (!res.ok) throw new Error(`Fires fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchModelMetrics() {
  const res = await fetch(`${API_BASE}/api/model/metrics`);
  if (!res.ok) throw new Error(`Metrics fetch failed: ${res.status}`);
  return res.json();
}

export async function triggerTraining() {
  const res = await fetch(`${API_BASE}/api/model/train`, { method: "POST" });
  if (!res.ok) throw new Error(`Training failed: ${res.status}`);
  return res.json();
}

export async function sendChatMessage(message, lat, lng, language = "en") {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, lat, lng, language }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
