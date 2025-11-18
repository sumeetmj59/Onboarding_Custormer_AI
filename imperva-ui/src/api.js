// src/lib/api.js

const DEFAULT_API_BASE = "https://onboarding-custormer-ai.onrender.com";

const API_BASE =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE) ||
  DEFAULT_API_BASE;

export async function evaluateNetwork(payload) {
  const url = `${API_BASE}/evaluate`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Backend error: ${res.status} (${res.statusText})`);
  }

  return await res.json();
}