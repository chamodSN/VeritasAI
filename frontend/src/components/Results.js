import React from 'react';

const Results = ({ cases, loading, error }) => {
  if (loading) {
    return (
      <div className="min-h-screen bg-legal-dark flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-accent-gold mx-auto mb-4"></div>
          <h2 className="text-2xl font-bold text-white mb-2">Analyzing Legal Cases</h2>
          <p className="text-gray-300">Our AI agents are processing your search...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-legal-dark flex items-center justify-center">
        <div className="max-w-md mx-auto text-center">
          <div className="w-16 h-16 bg-error-red/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-error-red" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Search Error</h2>
          <p className="text-gray-300 mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-legal-blue hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!cases || cases.length === 0) {
    return (
      <div className="min-h-screen bg-legal-dark flex items-center justify-center">
        <div className="max-w-md mx-auto text-center">
          <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">No Cases Found</h2>
          <p className="text-gray-300 mb-6">Try adjusting your search terms or filters to find relevant cases.</p>
          <button
            onClick={() => window.history.back()}
            className="bg-legal-blue hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            Back to Search
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-legal-dark py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Results Header */}
        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl shadow-legal p-6 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">Search Results</h1>
              <p className="text-gray-300">Found {cases.length} legal cases matching your criteria</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-success-green rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-300">AI Analysis Complete</span>
              </div>
              <div className="bg-legal-blue/20 text-legal-blue px-4 py-2 rounded-lg">
                <span className="text-sm font-medium">Multi-Agent Processed</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cases Grid */}
        <div className="grid gap-6">
          {cases.map((caseItem, index) => (
            <div
              key={caseItem.case_id || index}
              className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl shadow-legal overflow-hidden hover:shadow-legal-lg transition-all duration-200 hover:bg-gray-800/70"
            >
              <div className="p-6">
                {/* Case Header */}
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h2 className="text-2xl font-bold text-white leading-tight mb-3">
                      {caseItem.title || caseItem.case_name || "Unknown Case"}
                    </h2>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-300">
                      <span className="flex items-center space-x-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <span>{caseItem.court || "Unknown Court"}</span>
                      </span>
                      <span className="flex items-center space-x-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span>{caseItem.date || "Unknown Date"}</span>
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
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${caseItem.decision === "Reversed"
                      ? "bg-error-red/20 text-error-red"
                      : caseItem.decision === "Affirmed"
                        ? "bg-success-green/20 text-success-green"
                        : caseItem.decision === "Remanded"
                          ? "bg-warning-orange/20 text-warning-orange"
                          : "bg-gray-600/20 text-gray-300"
                      }`}>
                      {caseItem.decision || "Unknown"}
                    </span>
                  </div>
                </div>

                {/* AI Agent Processing Badges */}
                <div className="flex flex-wrap gap-2 mb-6">
                  <span className="bg-legal-blue/20 text-legal-blue text-xs font-medium px-3 py-1 rounded-full border border-legal-blue/30">
                    🔍 Case Finder
                  </span>
                  <span className="bg-success-green/20 text-success-green text-xs font-medium px-3 py-1 rounded-full border border-success-green/30">
                    📝 AI Summarizer
                  </span>
                  <span className="bg-accent-gold/20 text-accent-gold text-xs font-medium px-3 py-1 rounded-full border border-accent-gold/30">
                    📚 Citation Extractor
                  </span>
                  <span className="bg-purple-500/20 text-purple-400 text-xs font-medium px-3 py-1 rounded-full border border-purple-500/30">
                    🔗 Precedent Finder
                  </span>
                </div>

                {/* Case Summary */}
                <div className="mb-6">
                  <h3 className="font-semibold text-white mb-3 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    AI-Generated Summary
                  </h3>
                  <div className="bg-gray-700/50 p-4 rounded-lg border border-gray-600">
                    <p className="text-gray-200 leading-relaxed">
                      {caseItem.summary?.issue || caseItem.summary || "No summary available"}
                    </p>
                  </div>
                </div>

                {/* Legal Citations */}
                {caseItem.legal_citations && caseItem.legal_citations.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-white mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Legal Citations ({caseItem.legal_citations.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {caseItem.legal_citations.slice(0, 6).map((citation, cIdx) => (
                        <span
                          key={cIdx}
                          className="bg-legal-blue/20 text-white text-sm px-3 py-2 rounded-lg border border-legal-blue/30"
                        >
                          {citation}
                        </span>
                      ))}
                      {caseItem.legal_citations.length > 6 && (
                        <span className="bg-gray-600/20 text-gray-300 text-sm px-3 py-2 rounded-lg border border-gray-600/30">
                          +{caseItem.legal_citations.length - 6} more citations
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Related Precedents */}
                {caseItem.related_precedents && caseItem.related_precedents.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-white mb-3 flex items-center">
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      Related Precedents ({caseItem.related_precedents.length})
                    </h3>
                    <div className="space-y-3">
                      {caseItem.related_precedents.slice(0, 3).map((prec, pIdx) => (
                        <div
                          key={pIdx}
                          className="bg-gray-700/50 p-4 rounded-lg border-l-4 border-legal-blue"
                        >
                          <p className="font-medium text-white mb-1">
                            {prec.title || "Unknown Case"}
                          </p>
                          <p className="text-sm text-gray-300">
                            Court: {prec.court || "Unknown"} | Date: {prec.date || "Unknown"}
                          </p>
                        </div>
                      ))}
                      {caseItem.related_precedents.length > 3 && (
                        <div className="bg-gray-600/20 text-gray-300 text-sm px-4 py-3 rounded-lg border border-gray-600/30">
                          +{caseItem.related_precedents.length - 3} more related cases
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Back to Search */}
        <div className="mt-8 text-center">
          <button
            onClick={() => window.history.back()}
            className="bg-legal-blue hover:bg-blue-700 text-white px-8 py-3 rounded-lg transition-colors font-medium"
          >
            ← Back to Search
          </button>
        </div>
      </div>
    </div>
  );
};

export default Results;