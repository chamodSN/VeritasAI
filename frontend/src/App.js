import React, { useState } from 'react';
import axios from 'axios';
import './index.css';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');

  // Sample queries for quick testing
  const sampleQueries = [
    "What are the key legal issues in SCFR 531/2012?",
    "What precedents exist for writ applications?",
    "What are the constitutional rights violations?",
    "What defenses are available for public officers?",
    "How to prove Article 12(1) violations?"
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await axios.post(`${apiUrl}/api/query`, {
        query: query.trim()
      });

      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSampleQuery = (sampleQuery) => {
    setQuery(sampleQuery);
  };

  const ResultSection = ({ title, icon, iconColor, content }) => {
    if (!content) return null;
    
    return (
      <div className="card">
        <h3 className="text-xl font-bold text-gray-900 mb-4">
          <i className={`fas ${icon} mr-2 ${iconColor}`}></i>
          {title}
        </h3>
        <div className="prose max-w-none">
          <p className="text-gray-700 leading-relaxed">
            {typeof content === 'string' ? content : JSON.stringify(content)}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <i className="fas fa-balance-scale text-3xl text-primary-600"></i>
              </div>
              <div className="ml-4">
                <h1 className="text-3xl font-bold text-gray-900">VeritasAI</h1>
                <p className="text-sm text-gray-600">Legal Multi-Agent Research System</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                <i className="fas fa-server mr-2"></i>
                API: {apiUrl}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Query Input Section */}
        <div className="card mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            <i className="fas fa-search mr-2 text-primary-600"></i>
            Legal Query Interface
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                Enter your legal query:
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., What precedents should I review for environmental harm writ applications?"
                className="input-field"
                rows="3"
                disabled={loading}
              />
            </div>
            
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="btn-primary"
              >
                {loading ? (
                  <>
                    <i className="fas fa-spinner fa-spin mr-2"></i>
                    Processing...
                  </>
                ) : (
                  <>
                    <i className="fas fa-paper-plane mr-2"></i>
                    Submit Query
                  </>
                )}
              </button>
              
              <button
                type="button"
                onClick={() => setQuery('')}
                className="btn-secondary"
              >
                <i className="fas fa-times mr-2"></i>
                Clear
              </button>
            </div>
          </form>

          {/* Sample Queries */}
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Sample Queries:</h3>
            <div className="flex flex-wrap gap-2">
              {sampleQueries.map((sampleQuery, index) => (
                <button
                  key={index}
                  onClick={() => handleSampleQuery(sampleQuery)}
                  className="text-xs bg-gray-100 text-gray-700 px-3 py-1 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {sampleQuery}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <i className="fas fa-exclamation-triangle text-red-400 mt-1 mr-3"></i>
              <div>
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
                <p className="text-xs text-red-600 mt-2">
                  Make sure the VeritasAI server is running at {apiUrl}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Results Display */}
        {results && (
          <div className="space-y-6">
            <ResultSection
              title="Summary"
              icon="fa-file-alt"
              iconColor="text-green-600"
              content={results.summary}
            />

            <ResultSection
              title="Legal Issues Identified"
              icon="fa-gavel"
              iconColor="text-blue-600"
              content={results.issues}
            />

            <ResultSection
              title="Legal Arguments"
              icon="fa-comments"
              iconColor="text-purple-600"
              content={results.arguments}
            />

            <ResultSection
              title="Citations Verified"
              icon="fa-quote-left"
              iconColor="text-orange-600"
              content={results.citations}
            />

            <ResultSection
              title="Analytics & Patterns"
              icon="fa-chart-line"
              iconColor="text-teal-600"
              content={results.analytics}
            />

            {/* Confidence Score */}
            {results.confidence && (
              <div className="card">
                <h3 className="text-xl font-bold text-gray-900 mb-4">
                  <i className="fas fa-target mr-2 text-red-600"></i>
                  Confidence Score
                </h3>
                <div className="flex items-center">
                  <div className="flex-1 bg-gray-200 rounded-full h-4 mr-4">
                    <div 
                      className="bg-primary-600 h-4 rounded-full transition-all duration-500"
                      style={{ width: `${results.confidence * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-lg font-semibold text-gray-700">
                    {Math.round(results.confidence * 100)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        {!results && !loading && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-blue-800 mb-2">
              <i className="fas fa-info-circle mr-2"></i>
              How to Use VeritasAI
            </h3>
            <ul className="text-blue-700 space-y-2">
              <li>• Enter your legal query in the text area above</li>
              <li>• Click "Submit Query" to process your request</li>
              <li>• The system will analyze your legal documents and provide insights</li>
              <li>• Results include summaries, legal issues, arguments, and citations</li>
              <li>• Make sure the VeritasAI server is running at {apiUrl}</li>
            </ul>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-600">
            <p>&copy; 2024 VeritasAI Legal Multi-Agent System. Built with React & Tailwind CSS.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
