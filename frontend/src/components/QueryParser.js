import React, { useState } from "react";
import axios from "axios";

export default function QueryParser() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_URL = "http://localhost:8001/parse_query";
  const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaGFtb2QiLCJleHAiOjE3NTY4MTUxODl9.VF6seQE5tzPNuw0PmvYwic4YC9gv3hTDVsb_Iw1CLSw";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      setError("Please enter a query!");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await axios.post(
        API_URL,
        { query },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${TOKEN}`,
          },
        }
      );

      setResult(res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Something went wrong. Try again later."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center bg-gray-100 py-10 px-4">
      <div className="bg-white shadow-lg rounded-xl p-6 w-full max-w-lg">
        <h1 className="text-2xl font-bold mb-4 text-gray-800">
          Query Understanding & Case Retrieval
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="e.g. Show me Supreme Court cases about Intellectual Property from Q2 2023"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
          >
            {loading ? "Parsing..." : "Parse Query"}
          </button>
        </form>

        {/* Error */}
        {error && <p className="text-red-500 text-sm mt-3">{error}</p>}

        {/* Result */}
        {result && (
          <div className="mt-6 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <h2 className="text-lg font-semibold mb-2 text-gray-700">Parsed Result:</h2>
            <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto text-sm text-gray-800">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
