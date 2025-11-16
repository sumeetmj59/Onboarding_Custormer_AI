// src/api.js

const API_BASE = 'http://127.0.0.1:8000';

export async function evaluateNetwork(payload) {
  const res = await fetch(`${API_BASE}/evaluate/ai`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error ${res.status}: ${text}`);
  }
  return res.json();
}