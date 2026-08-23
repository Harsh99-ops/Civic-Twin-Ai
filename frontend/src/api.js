const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export function getHealth() {
  return fetch(`${API_BASE}/health`).then(handle);
}

export function getComplaints(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return fetch(`${API_BASE}/complaints${qs ? `?${qs}` : ""}`).then(handle);
}

export function getStats() {
  return fetch(`${API_BASE}/stats`).then(handle);
}

export function getRiskZones(topN = 20) {
  return fetch(`${API_BASE}/risk-zones?top_n=${topN}`).then(handle);
}

export function getPrioritize(budget, topN = 50) {
  return fetch(`${API_BASE}/prioritize?budget=${budget}&top_n=${topN}`).then(handle);
}

export function reportIssue({ latitude, longitude, category, file }) {
  const form = new FormData();
  form.append("latitude", latitude);
  form.append("longitude", longitude);
  form.append("category", category);
  if (file) form.append("file", file);
  return fetch(`${API_BASE}/report`, { method: "POST", body: form }).then(handle);
}

export function sendChatMessage(message) {
  return fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  }).then(handle);
}

export { API_BASE };
