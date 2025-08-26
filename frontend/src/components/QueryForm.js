import { useState } from "react";

export default function QueryForm({ onResults }) {
  const [query, setQuery] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [dateRange, setDateRange] = useState("");
  const [topK, setTopK] = useState(5);

  async function handleSubmit(e) {
    e.preventDefault();
    const { queryCases } = await import("../api");
    const results = await queryCases(query, jurisdiction, dateRange, topK);
    onResults(results);
  }

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Query:</label>
        <input value={query} onChange={e => setQuery(e.target.value)} />
      </div>
      <div>
        <label>Jurisdiction:</label>
        <input value={jurisdiction} onChange={e => setJurisdiction(e.target.value)} />
      </div>
      <div>
        <label>Date Range:</label>
        <input value={dateRange} onChange={e => setDateRange(e.target.value)} />
      </div>
      <div>
        <label>Top K:</label>
        <input
          type="number"
          value={topK}
          onChange={e => setTopK(Number(e.target.value))}
        />
      </div>
      <button type="submit">Search</button>
    </form>
  );
}