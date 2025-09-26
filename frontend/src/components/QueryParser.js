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
  const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaGFtb2QiLCJleHAiOjE3NTg4NjA0NTR9.3de5lytyPAYZl-fXhVDUL4XXkQgCgDHX17LlG-ZHaYI";

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
    <div className="min-h-screen bg-legal-dark">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-legal-dark via-legal-blue to-legal-dark text-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            Advanced Legal Case Research
          </h1>
          <p className="text-xl text-gray-200 mb-8 max-w-2xl mx-auto">
            Discover, analyze, and understand legal cases with AI-powered multi-agent research system
          </p>

          {/* Search Form */}
          <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="e.g., Supreme Court decisions on Fourth Amendment search and seizure after 2018"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full px-6 py-4 text-gray-900 bg-white rounded-xl border-0 focus:outline-none focus:ring-4 focus:ring-accent-gold/30 text-lg placeholder-gray-500"
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-accent-gold hover:bg-yellow-500 text-legal-dark font-semibold px-8 py-4 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-lg"
              >
                {loading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-legal-dark"></div>
                    <span>Searching Cases...</span>
                  </div>
                ) : (
                  "Search Legal Cases"
                )}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-legal-dark">
        {error && (
          <div className="bg-error-red/10 border border-error-red/20 text-error-red px-6 py-4 rounded-lg mb-6">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">Error: {error}</span>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-6">
            {/* Results Header */}
            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl shadow-legal p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold text-white">Search Results</h2>
                <div className="flex items-center space-x-2 text-sm text-gray-300">
                  <span className="bg-success-green/10 text-success-green px-3 py-1 rounded-full">
                    {result.cases?.length || 0} Cases Found
                  </span>
                </div>
              </div>

              {/* Filters and Sorting */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Court Filter</label>
                  <input
                    type="text"
                    value={courtFilter}
                    onChange={(e) => setCourtFilter(e.target.value)}
                    placeholder="Filter by court"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-blue placeholder-gray-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Min Citations</label>
                  <input
                    type="number"
                    min="0"
                    value={minCitations}
                    onChange={(e) => setMinCitations(e.target.value)}
                    placeholder="Min citations"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-blue placeholder-gray-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Sort By</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-blue"
                  >
                    <option>Newest</option>
                    <option>Oldest</option>
                    <option>Most Cited</option>
                    <option>Least Cited</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Results Per Page</label>
                  <select
                    value={perPage}
                    onChange={(e) => setPerPage(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-legal-blue"
                  >
                    <option value={5}>5 per page</option>
                    <option value={10}>10 per page</option>
                    <option value={20}>20 per page</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Cases List */}
            {(!result.cases || result.cases.length === 0) ? (
              <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl shadow-legal p-12 text-center">
                <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-white mb-2">No cases found</h3>
                <p className="text-gray-300">Try adjusting your search terms or filters to find relevant cases.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {sortedAndFilteredCases().map((caseItem) => (
                  <div
                    key={caseItem.case_id}
                    className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl shadow-legal overflow-hidden hover:shadow-legal-lg transition-all duration-200 hover:bg-gray-800/70"
                  >
                    <div className="p-6">
                      {/* Case Header */}
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex-1">
                          <h3 className="text-xl font-bold text-white leading-tight mb-2">
                            {caseItem.title || caseItem.summary?.case || "Unknown Case"}
                          </h3>
                          <div className="flex items-center space-x-4 text-sm text-gray-300">
                            <span className="flex items-center space-x-1">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                              </svg>
                              <span>{caseItem.court || caseItem.summary?.court || "Unknown Court"}</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                              <span>{caseItem.date || caseItem.related_precedents?.[0]?.date || "Unknown Date"}</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <span>{caseItem.citations_count || 0} Citations</span>
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${(caseItem.decision || caseItem.summary?.decision) === "Reversed"
                              ? "bg-error-red/10 text-error-red"
                              : (caseItem.decision || caseItem.summary?.decision) === "Affirmed"
                                ? "bg-success-green/10 text-success-green"
                                : (caseItem.decision || caseItem.summary?.decision) === "Remanded"
                                  ? "bg-warning-orange/10 text-warning-orange"
                                  : "bg-gray-100 text-gray-600"
                            }`}>
                            {caseItem.decision || caseItem.summary?.decision || "Unknown"}
                          </span>
                        </div>
                      </div>

                      {/* AI Agent Badges */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        <span className="bg-legal-blue/10 text-legal-blue text-xs font-medium px-2 py-1 rounded-full">
                          Found by Case Finder
                        </span>
                        <span className="bg-success-green/10 text-success-green text-xs font-medium px-2 py-1 rounded-full">
                          Summarized by AI
                        </span>
                        <span className="bg-accent-gold/10 text-accent-gold text-xs font-medium px-2 py-1 rounded-full">
                          Citations Extracted
                        </span>
                        <span className="bg-purple-100 text-purple-800 text-xs font-medium px-2 py-1 rounded-full">
                          Precedents Linked
                        </span>
                      </div>

                      {/* Case Summary */}
                      <div className="mb-6">
                        <h4 className="font-semibold text-white mb-3 flex items-center">
                          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          Case Summary
                        </h4>
                        <p className="text-gray-200 leading-relaxed bg-gray-700/50 p-4 rounded-lg border border-gray-600">
                          {caseItem.summary?.issue || "No summary available"}
                        </p>
                        {caseItem.summary?.entities && (
                          <div className="mt-3">
                            <h5 className="font-medium text-gray-300 mb-2">Key Entities:</h5>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(caseItem.summary.entities).map(([type, entities]) =>
                                entities.length > 0 ? (
                                  <div key={type} className="text-sm">
                                    <span className="font-medium text-gray-300">{type}:</span>
                                    <span className="text-gray-200 ml-1">{entities.join(", ")}</span>
                                  </div>
                                ) : null
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Legal Citations */}
                      {caseItem.legal_citations && caseItem.legal_citations.length > 0 && (
                        <div className="mb-6">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-semibold text-white flex items-center">
                              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              Legal Citations ({caseItem.legal_citations.length})
                            </h4>
                            <button
                              className="text-accent-gold hover:text-yellow-400 text-sm font-medium transition-colors"
                              onClick={() => toggleExpanded(`${caseItem.case_id}-cits`)}
                            >
                              {expanded[`${caseItem.case_id}-cits`] ? "Collapse" : "Expand"}
                            </button>
                          </div>
                          {expanded[`${caseItem.case_id}-cits`] && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {caseItem.legal_citations.map((citation, cIdx) => (
                                <span
                                  key={cIdx}
                                  className="bg-legal-blue/20 text-legal-blue text-sm px-3 py-2 rounded-lg border border-legal-blue/30"
                                >
                                  {citation}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Related Precedents */}
                      {caseItem.related_precedents && caseItem.related_precedents.length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-semibold text-white flex items-center">
                              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                              </svg>
                              Related Precedents ({caseItem.related_precedents.length})
                            </h4>
                            <button
                              className="text-accent-gold hover:text-yellow-400 text-sm font-medium transition-colors"
                              onClick={() => toggleExpanded(`${caseItem.case_id}-prec`)}
                            >
                              {expanded[`${caseItem.case_id}-prec`] ? "Collapse" : "Expand"}
                            </button>
                          </div>
                          {expanded[`${caseItem.case_id}-prec`] && (
                            <div className="space-y-3">
                              {caseItem.related_precedents.map((prec, pIdx) => (
                                <div
                                  key={pIdx}
                                  className="bg-gray-700/50 p-4 rounded-lg border-l-4 border-legal-blue"
                                >
                                  <p className="font-medium text-white mb-1">
                                    {prec.title || "Unknown Case"}
                                  </p>
                                  <p className="text-sm text-gray-300">
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
          </div>
        )}
      </div>
    </div>
  );
}