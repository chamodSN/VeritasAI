import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './index.css';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);

  // Sample queries for CourtListener API testing
  const sampleQueries = [
    "contract breach damages remedies",
    "constitutional rights violations first amendment",
    "employment discrimination workplace harassment",
    "intellectual property patent infringement",
    "criminal procedure fourth amendment search",
    "family law divorce custody rights",
    "bankruptcy debt relief chapter 7",
    "environmental law pollution regulations",
    "tax law deductions exemptions",
    "property law real estate disputes"
  ];

  // Authentication functions
  const getAuthToken = () => {
    return localStorage.getItem('authToken');
  };

  const setAuthToken = (token) => {
    localStorage.setItem('authToken', token);
  };

  const removeAuthToken = () => {
    localStorage.removeItem('authToken');
  };

  const checkAuthStatus = async () => {
    const token = getAuthToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${apiUrl}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Auth check failed:', error);
      removeAuthToken();
    } finally {
      setAuthLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${apiUrl}/api/auth/google`;
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${apiUrl}/api/auth/logout`);
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      removeAuthToken();
      setUser(null);
      setIsAuthenticated(false);
      setResults(null);
    }
  };

  // Handle OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
      setAuthToken(token);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
      // Check auth status
      checkAuthStatus();
    } else {
      checkAuthStatus();
    }
  }, [apiUrl]);

  // Create axios instance with auth header
  const apiClient = axios.create({
    baseURL: apiUrl,
    headers: {
      'Content-Type': 'application/json',
    }
  });

  // Add auth interceptor
  apiClient.interceptors.request.use((config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await apiClient.post('/api/query', {
        query: query.trim()
      });

      setResults(response.data);
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Please log in to submit queries');
        setIsAuthenticated(false);
        removeAuthToken();
      } else {
        setError(err.response?.data?.detail || err.message);
      }
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
                <p className="text-sm text-gray-600">Legal Multi-Agent Research System with CourtListener API</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                <i className="fas fa-server mr-2"></i>
                API: {apiUrl}
              </div>

              {/* Authentication Section */}
              {authLoading ? (
                <div className="text-sm text-gray-500">
                  <i className="fas fa-spinner fa-spin mr-2"></i>
                  Checking authentication...
                </div>
              ) : isAuthenticated ? (
                <div className="flex items-center space-x-3">
                  <div className="text-sm text-gray-600">
                    <i className="fas fa-user mr-2"></i>
                    {user?.email}
                  </div>
                  <button
                    onClick={handleLogout}
                    className="text-sm bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
                  >
                    <i className="fas fa-sign-out-alt mr-1"></i>
                    Logout
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleGoogleLogin}
                  className="text-sm bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 flex items-center"
                >
                  <i className="fab fa-google mr-2"></i>
                  Login with Google
                </button>
              )}
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

          {!isAuthenticated ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <div className="flex items-center">
                <i className="fas fa-exclamation-triangle text-yellow-400 mr-3"></i>
                <div>
                  <h3 className="text-sm font-medium text-yellow-800">Authentication Required</h3>
                  <p className="text-sm text-yellow-700 mt-1">
                    Please log in with Google to submit legal queries and access your query history.
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                Enter your legal query:
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., contract breach damages remedies, constitutional rights violations, employment discrimination..."
                className="input-field"
                rows="3"
                disabled={loading || !isAuthenticated}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={loading || !query.trim() || !isAuthenticated}
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

            {/* Case Count and Source */}
            {results.case_count && (
              <div className="card">
                <h3 className="text-xl font-bold text-gray-900 mb-4">
                  <i className="fas fa-database mr-2 text-indigo-600"></i>
                  Search Results
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="flex items-center">
                      <i className="fas fa-file-alt text-blue-600 mr-3"></i>
                      <div>
                        <p className="text-sm font-medium text-blue-800">Cases Found</p>
                        <p className="text-2xl font-bold text-blue-900">{results.case_count}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="flex items-center">
                      <i className="fas fa-server text-green-600 mr-3"></i>
                      <div>
                        <p className="text-sm font-medium text-green-800">Data Source</p>
                        <p className="text-lg font-bold text-green-900">{results.source || 'CourtListener API'}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

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
              <li>• Enter your legal query using keywords (e.g., "contract breach", "constitutional rights")</li>
              <li>• Click "Submit Query" to search CourtListener API for relevant cases</li>
              <li>• The system will analyze federal court cases and provide comprehensive insights</li>
              <li>• Results include case summaries, legal issues, arguments, and verified citations</li>
              <li>• Try the sample queries below to get started</li>
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