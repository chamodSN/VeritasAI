import React, { useState } from "react";
import axios from "axios";

export default function QueryParser() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [courtFilter, setCourtFilter] = useState("");
  const [minCitations, setMinCitations] = useState(0);
  const [sortBy, setSortBy] = useState("Newest");
  const [expanded, setExpanded] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_URL = "http://localhost:8000/query";
  const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaGFtb2QiLCJleHAiOjE3NTg3ODIwNDR9.rkapnVeYt1twN_J7y8NKty5u96p1XudcQnCd5_vm-Tc";

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
        { query, page, per_page: perPage },
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${TOKEN}`,
          },
        }
      );
      setResult(res.data);
    } catch (err) {
      console.error("API Error:", err);
      console.error("Response:", err.response?.data);
      console.error("Status:", err.response?.status);

      let errorMessage = "Something went wrong. Try again later.";
      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.response?.status === 401) {
        errorMessage = "Authentication failed. Please refresh the page.";
      } else if (err.response?.status === 500) {
        errorMessage = "Server error. Please try again later.";
      } else if (err.code === "ECONNREFUSED") {
        errorMessage = "Cannot connect to server. Please ensure the backend is running.";
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (id) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const sortedAndFilteredCases = () => {
    if (!result?.cases) return [];
    let cases = [...result.cases];
    // Filter by court
    if (courtFilter) {
      cases = cases.filter((c) =>
        (c.court || c.summary?.court || "").toLowerCase().includes(courtFilter.toLowerCase())
      );
    }
    // Filter by citations count
    cases = cases.filter((c) => (c.citations_count || 0) >= (Number(minCitations) || 0));
    // Sort
    const getCaseDate = (caseItem) => {
      if (caseItem.date) return caseItem.date;
      if (caseItem.related_precedents?.[0]?.date) return caseItem.related_precedents[0].date;
      return "";
    };
    if (sortBy === "Newest") {
      cases.sort((a, b) => (getCaseDate(b) || "").localeCompare(getCaseDate(a) || ""));
    } else if (sortBy === "Oldest") {
      cases.sort((a, b) => (getCaseDate(a) || "").localeCompare(getCaseDate(b) || ""));
    } else if (sortBy === "Most Cited") {
      cases.sort((a, b) => (b.citations_count || 0) - (a.citations_count || 0));
    } else if (sortBy === "Least Cited") {
      cases.sort((a, b) => (a.citations_count || 0) - (b.citations_count || 0));
    }
    return cases;
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
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <h2 className="text-lg font-semibold text-blue-800">Search Results</h2>
              <div className="text-sm text-blue-600 mt-1">
                <span className="font-medium">Search:</span> {result.query?.topic || "N/A"} |{" "}
                {result.query?.date_range || "Any time"} | {result.total_results || 0} Cases Found
              </div>
            </div>

            {/* Filters and Sorting */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
              <input
                type="text"
                value={courtFilter}
                onChange={(e) => setCourtFilter(e.target.value)}
                placeholder="Filter by court"
                className="p-2 border rounded"
              />
              <input
                type="number"
                min="0"
                value={minCitations}
                onChange={(e) => setMinCitations(e.target.value)}
                placeholder="Min citations"
                className="p-2 border rounded"
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="p-2 border rounded"
              >
                <option>Newest</option>
                <option>Oldest</option>
                <option>Most Cited</option>
                <option>Least Cited</option>
              </select>
              <select
                value={perPage}
                onChange={(e) => setPerPage(Number(e.target.value))}
                className="p-2 border rounded"
              >
                <option value={5}>5 / page</option>
                <option value={10}>10 / page</option>
                <option value={20}>20 / page</option>
              </select>
            </div>

            {(!result.cases || result.cases.length === 0) ? (
              <div className="text-center py-8">
                <p className="text-gray-600 text-lg">No cases found matching your criteria.</p>
                <p className="text-gray-500 text-sm mt-2">Try adjusting your search terms or date range.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {sortedAndFilteredCases().map((caseItem) => (
                  <div
                    key={caseItem.case_id}
                    className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden"
                  >
                    <div className="p-6">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-xl font-bold text-gray-900 leading-tight">
                          {caseItem.title || caseItem.summary?.case || "Unknown Case"}
                        </h3>
                        <div className="flex items-center gap-2">
                          <span className="bg-purple-100 text-purple-800 text-xs font-medium px-2 py-0.5 rounded">
                            Found by Case Finder
                          </span>
                          <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded">
                            Summarized by Summarizer AI
                          </span>
                          <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded">
                            Linked by Citation AI
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div className="space-y-2">
                          <p className="text-sm">
                            <span className="font-semibold text-gray-700">Court:</span>{" "}
                            <span className="ml-2 text-gray-900">
                              {caseItem.court || caseItem.summary?.court || "Unknown"}
                            </span>
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold text-gray-700">Decision:</span>{" "}
                            <span
                              className={`ml-2 px-2 py-1 rounded text-xs font-medium ${(caseItem.decision || caseItem.summary?.decision) === "Reversed"
                                ? "bg-red-100 text-red-800"
                                : (caseItem.decision || caseItem.summary?.decision) === "Affirmed"
                                  ? "bg-green-100 text-green-800"
                                  : (caseItem.decision || caseItem.summary?.decision) === "Remanded"
                                    ? "bg-yellow-100 text-yellow-800"
                                    : "bg-gray-100 text-gray-800"
                                }`}
                            >
                              {caseItem.decision || caseItem.summary?.decision || "Unknown"}
                            </span>
                          </p>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm">
                            <span className="font-semibold text-gray-700">Docket:</span>{" "}
                            <span className="ml-2 font-mono text-gray-900">
                              {caseItem.docket_id || caseItem.case_id}
                            </span>
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold text-gray-700">Citations:</span>{" "}
                            <span className="ml-2 text-gray-900">{caseItem.citations_count || 0}</span>
                          </p>
                          <p className="text-sm">
                            <span className="font-semibold text-gray-700">Date:</span>{" "}
                            <span className="ml-2 text-gray-900">
                              {caseItem.date || caseItem.related_precedents?.[0]?.date || "Unknown"}
                            </span>
                          </p>
                        </div>
                      </div>

                      <div className="mb-4">
                        <h4 className="font-semibold text-gray-700 mb-2">Case Summary:</h4>
                        <p className="text-gray-800 leading-relaxed">
                          {caseItem.summary?.issue || "No summary available"}
                        </p>
                        {caseItem.summary?.entities && (
                          <div className="mt-2">
                            <h5 className="font-semibold text-gray-600">Entities:</h5>
                            <ul className="text-sm text-gray-700 list-disc list-inside">
                              {Object.entries(caseItem.summary.entities).map(([type, entities]) =>
                                entities.length > 0 ? (
                                  <li key={type}>
                                    {type.charAt(0).toUpperCase() + type.slice(1)}: {entities.join(", ")}
                                  </li>
                                ) : null
                              )}
                            </ul>
                          </div>
                        )}
                      </div>

                      {caseItem.legal_citations && caseItem.legal_citations.length > 0 && (
                        <div className="mb-4">
                          <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-gray-700 mb-2">Legal Citations</h4>
                            <button
                              className="text-sm text-blue-600"
                              onClick={() => toggleExpanded(`${caseItem.case_id}-cits`)}
                            >
                              {expanded[`${caseItem.case_id}-cits`] ? "Collapse" : "Expand"}
                            </button>
                          </div>
                          {expanded[`${caseItem.case_id}-cits`] && (
                            <div className="flex flex-wrap gap-2">
                              {caseItem.legal_citations.map((citation, cIdx) => (
                                <span
                                  key={cIdx}
                                  className="bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded"
                                >
                                  {citation}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {caseItem.related_precedents && caseItem.related_precedents.length > 0 && (
                        <div>
                          <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-gray-700 mb-2">Related Precedents</h4>
                            <button
                              className="text-sm text-blue-600"
                              onClick={() => toggleExpanded(`${caseItem.case_id}-prec`)}
                            >
                              {expanded[`${caseItem.case_id}-prec`] ? "Collapse" : "Expand"}
                            </button>
                          </div>
                          {expanded[`${caseItem.case_id}-prec`] && (
                            <div className="space-y-2">
                              {caseItem.related_precedents.map((prec, pIdx) => (
                                <div
                                  key={pIdx}
                                  className="bg-gray-50 p-3 rounded border-l-4 border-blue-200"
                                >
                                  <p className="font-medium text-gray-900">
                                    {prec.title || "Unknown Case"}
                                  </p>
                                  <p className="text-sm text-gray-600">
                                    Court: {prec.court || "Unknown"} | Date: {prec.date || "Unknown"} | ID: {prec.id || "Unknown"}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* Pagination Controls */}
            {result.pagination && (
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-gray-600">
                  Page {result.pagination.page} of {result.pagination.total_pages} • {result.total_results} results •{" "}
                  {result.execution_time_ms} ms
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="px-3 py-1 rounded border bg-white disabled:opacity-50"
                    disabled={result.pagination.page <= 1 || loading}
                    onClick={() => {
                      setPage((p) => Math.max(1, p - 1));
                      setResult(null);
                      setTimeout(() => handleSubmit(new Event("submit")), 0);
                    }}
                  >
                    Prev
                  </button>
                  <button
                    className="px-3 py-1 rounded border bg-white disabled:opacity-50"
                    disabled={result.pagination.page >= result.pagination.total_pages || loading}
                    onClick={() => {
                      setPage((p) => p + 1);
                      setResult(null);
                      setTimeout(() => handleSubmit(new Event("submit")), 0);
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}