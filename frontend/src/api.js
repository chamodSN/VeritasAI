const API_BASE = "http://127.0.0.1:8000"; // orchestrator service

export async function queryCases(query, jurisdiction, dateRange, topK) {
  const resp = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      jurisdiction,
      date_range: dateRange,
      top_k: topK,
    }),
  });
  return await resp.json();
}














