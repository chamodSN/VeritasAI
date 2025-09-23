// frontend/components/QueryParser.js (Updated to handle better display and fallbacks)
import React, { useState } from "react";
import axios from "axios";

export default function QueryParser() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_URL = "http://localhost:8000/query"; // Orchestrator endpoint
  const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaGFtb2QiLCJleHAiOjE3NTc0MjE4OTh9.UwRVrX2fvzzusn5i03nrVrqEOyW9g5kLjMbfuYK2u5s";

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
      <div className="bg-white shadow-lg rounded-xl p-6 w-full max-w-3xl">
        <h1 className="text-2xl font-bold mb-4 text-gray-800">
          Legal Case Researcher
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="e.g. Show me Supreme Court cases about cyber fraud from 2020 to 2025"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg transition disabled:opacity-50"
          >
            {loading ? "Searching..." : "Search Cases"}
          </button>
        </form>

        {error && <p className="text-red-500 text-sm mt-3">{error}</p>}

        {result && (
          <div className="mt-6 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <h2 className="text-lg font-semibold mb-2 text-gray-700">Search Results:</h2>
            {result.cases.length === 0 ? (
              <p className="text-gray-600">No cases found.</p>
            ) : (
              result.cases.map((caseItem, index) => (
                <div key={caseItem.case_id} className="mb-4 p-4 bg-white rounded-lg shadow">
                  <h3 className="text-md font-semibold text-gray-800">
                    {caseItem.case_name !== "Unknown" ? caseItem.case_name : (caseItem.summary.case || "Unknown Case")}
                  </h3>
                  <p className="text-sm text-gray-600"><strong>Court:</strong> {caseItem.court !== "Unknown" ? caseItem.court : (caseItem.summary.court || "Unknown")}</p>
                  <p className="text-sm text-gray-600"><strong>Decision:</strong> {caseItem.decision !== "Unknown" ? caseItem.decision : (caseItem.summary.decision || "Unknown")}</p>
                  <p className="text-sm text-gray-600"><strong>Summary:</strong> {caseItem.summary.issue || "No summary available"}</p>
                  <p className="text-sm text-gray-600"><strong>Citations:</strong> {caseItem.citations.length > 0 ? caseItem.citations.join(", ") : "None"}</p>
                  <p className="text-sm text-gray-600"><strong>Related Precedents:</strong></p>
                  <ul className="list-disc pl-5">
                    {caseItem.related_precedents.length > 0 ? (
                      caseItem.related_precedents.map((prec, pIdx) => (
                        <li key={pIdx} className="text-sm text-gray-600">
                          {prec.case_name} (ID: {prec.case_id}, Court: {prec.court}, Date: {prec.date_filed})
                        </li>
                      ))
                    ) : (
                      <li>No related precedents found.</li>
                    )}
                  </ul>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}