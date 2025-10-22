import React, { useState, useEffect } from 'react';
import axios from 'axios';
import PDFUpload from './components/PDFUpload';
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
  const [history, setHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('query');

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

  // Fetch history when user is authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchHistory();
    }
  }, [isAuthenticated]);

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

  const handlePDFAnalysisComplete = (analysisResults) => {
    setResults(analysisResults);
    setError(null);
  };

  const fetchHistory = async () => {
    if (!isAuthenticated) return;
    
    setHistoryLoading(true);
    try {
      const response = await apiClient.get('/api/user/history');
      setHistory(response.data);
    } catch (err) {
      console.error('Error fetching history:', err);
      setError('Failed to load history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const ResultSection = ({ title, icon, iconColor, content }) => {
    if (!content) return null;

    // Special handling for citations
    if (title === "Citations Verified" && typeof content === 'object') {
      return <CitationsSection content={content} />;
    }

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

  const CitationsSection = ({ content }) => {
    // Parse the citation data
    let citationData = null;
    let summary = null;
    
    try {
      // First try to use parsed_data if available
      if (content.parsed_data) {
        citationData = content.parsed_data;
      } else {
        // Fallback to parsing from raw_result or verification_details
        const rawData = content.raw_result || content.verification_details;
        if (rawData && typeof rawData === 'string') {
          // Extract JSON from markdown code blocks
          const jsonMatch = rawData.match(/```json\n([\s\S]*?)\n```/);
          if (jsonMatch) {
            citationData = JSON.parse(jsonMatch[1]);
          } else {
            // Try to find JSON without code blocks
            const jsonMatch2 = rawData.match(/\{[\s\S]*\}/);
            if (jsonMatch2) {
              citationData = JSON.parse(jsonMatch2[0]);
            }
          }
        }
      }
      
      // Get summary info
      summary = {
        total: content.total_citations || 0,
        status: content.status || 'unknown',
        message: content.message || ''
      };
    } catch (e) {
      console.error('Error parsing citation data:', e);
    }

    if (!citationData && !summary) {
      return (
        <div className="card">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            <i className="fas fa-quote-left mr-2 text-orange-600"></i>
            Citations Verified
          </h3>
          <div className="prose max-w-none">
            <p className="text-gray-700 leading-relaxed">
              {typeof content === 'string' ? content : JSON.stringify(content)}
            </p>
          </div>
        </div>
      );
    }

    const { overall_verification_summary, individual_citation_analysis } = citationData || {};
    const citations = individual_citation_analysis || [];

    return (
      <div className="card">
        <h3 className="text-xl font-bold text-gray-900 mb-4">
          <i className="fas fa-quote-left mr-2 text-orange-600"></i>
          Citations Verified
        </h3>
        
        {/* Summary Stats */}
        {overall_verification_summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-green-50 p-3 rounded-lg text-center">
              <div className="text-2xl font-bold text-green-600">{overall_verification_summary.valid}</div>
              <div className="text-sm text-green-700">Valid</div>
            </div>
            <div className="bg-red-50 p-3 rounded-lg text-center">
              <div className="text-2xl font-bold text-red-600">{overall_verification_summary.invalid}</div>
              <div className="text-sm text-red-700">Invalid</div>
            </div>
            <div className="bg-yellow-50 p-3 rounded-lg text-center">
              <div className="text-2xl font-bold text-yellow-600">{overall_verification_summary.needs_review}</div>
              <div className="text-sm text-yellow-700">Needs Review</div>
            </div>
            <div className="bg-blue-50 p-3 rounded-lg text-center">
              <div className="text-2xl font-bold text-blue-600">{overall_verification_summary.format_compliance_score}%</div>
              <div className="text-sm text-blue-700">Compliance</div>
            </div>
          </div>
        )}

        {/* Status Message */}
        {summary.message && (
          <div className={`p-3 rounded-lg mb-4 ${
            summary.status === 'completed' ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
          }`}>
            <div className="flex items-center">
              <i className={`fas ${
                summary.status === 'completed' ? 'fa-check-circle text-green-600' : 'fa-exclamation-triangle text-yellow-600'
              } mr-2`}></i>
              <span className={`text-sm font-medium ${
                summary.status === 'completed' ? 'text-green-800' : 'text-yellow-800'
              }`}>
                {summary.message}
              </span>
            </div>
          </div>
        )}

        {/* Citations List */}
        {citations.length > 0 && (
          <div>
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Citation Analysis</h4>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {citations.map((citation, index) => (
                <div key={index} className={`p-4 rounded-lg border ${
                  citation.status === 'VALID' ? 'bg-green-50 border-green-200' :
                  citation.status === 'INVALID' ? 'bg-red-50 border-red-200' :
                  'bg-yellow-50 border-yellow-200'
                }`}>
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h5 className="font-medium text-gray-900">{citation.citation}</h5>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          citation.status === 'VALID' ? 'bg-green-100 text-green-800' :
                          citation.status === 'INVALID' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {citation.status}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          citation.confidence_level === 'HIGH' ? 'bg-green-100 text-green-800' :
                          citation.confidence_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {citation.confidence_level} Confidence
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {citation.issues && citation.issues !== 'None' && (
                    <div className="mt-2">
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">Issues:</span> {citation.issues}
                      </p>
                    </div>
                  )}
                  
                  {citation.recommendations && citation.recommendations !== 'None needed.' && (
                    <div className="mt-2">
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">Recommendations:</span> {citation.recommendations}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Fallback for unparseable content */}
        {!citationData && summary && (
          <div className="prose max-w-none">
            <p className="text-gray-700 leading-relaxed">
              <strong>Status:</strong> {summary.status}<br/>
              <strong>Message:</strong> {summary.message}<br/>
              <strong>Total Citations:</strong> {summary.total}
            </p>
          </div>
        )}
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
                <p className="text-sm text-gray-600">Legal Multi-Agent Research System with CourtListener API & PDF Analysis</p>
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

      {/* Tab Navigation */}
      {isAuthenticated && (
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex space-x-8">
              <button
                onClick={() => setActiveTab('query')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'query'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <i className="fas fa-search mr-2"></i>
                New Query
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'history'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <i className="fas fa-history mr-2"></i>
                History
                {history && (
                  <span className="ml-2 bg-primary-100 text-primary-800 text-xs px-2 py-1 rounded-full">
                    {history.total_queries + history.total_results}
                  </span>
                )}
              </button>
            </nav>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Query Tab Content */}
        {activeTab === 'query' && (
          <>
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

        {/* PDF Upload Section */}
        <PDFUpload 
          apiClient={apiClient}
          isAuthenticated={isAuthenticated}
          onAnalysisComplete={handlePDFAnalysisComplete}
        />

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
              <li>• Upload PDF documents for direct analysis of legal cases and documents</li>
              <li>• The system will analyze federal court cases and provide comprehensive insights</li>
              <li>• Results include case summaries, legal issues, arguments, and verified citations</li>
              <li>• Try the sample queries below to get started</li>
              <li>• Make sure the VeritasAI server is running at {apiUrl}</li>
            </ul>
          </div>
        )}
          </>
        )}

        {/* History Tab Content */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="card">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  <i className="fas fa-history mr-2 text-primary-600"></i>
                  Query History
                </h2>
                <button
                  onClick={fetchHistory}
                  disabled={historyLoading}
                  className="btn-secondary"
                >
                  {historyLoading ? (
                    <>
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      Loading...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-refresh mr-2"></i>
                      Refresh
                    </>
                  )}
                </button>
              </div>

              {historyLoading ? (
                <div className="text-center py-8">
                  <i className="fas fa-spinner fa-spin text-2xl text-gray-400 mb-4"></i>
                  <p className="text-gray-600">Loading your history...</p>
                </div>
              ) : history ? (
                <div className="space-y-6">
                  {/* Summary Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="flex items-center">
                        <i className="fas fa-search text-blue-600 mr-3"></i>
                        <div>
                          <p className="text-sm font-medium text-blue-800">Total Queries</p>
                          <p className="text-2xl font-bold text-blue-900">{history.total_queries}</p>
                        </div>
                      </div>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="flex items-center">
                        <i className="fas fa-file-alt text-green-600 mr-3"></i>
                        <div>
                          <p className="text-sm font-medium text-green-800">Total Results</p>
                          <p className="text-2xl font-bold text-green-900">{history.total_results}</p>
                        </div>
                      </div>
                    </div>
                    <div className="bg-purple-50 p-4 rounded-lg">
                      <div className="flex items-center">
                        <i className="fas fa-chart-line text-purple-600 mr-3"></i>
                        <div>
                          <p className="text-sm font-medium text-purple-800">Avg Confidence</p>
                          <p className="text-2xl font-bold text-purple-900">
                            {history.results.length > 0 
                              ? Math.round((history.results.reduce((sum, r) => sum + (r.confidence || 0), 0) / history.results.length) * 100)
                              : 0}%
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recent Queries */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      <i className="fas fa-clock mr-2 text-gray-600"></i>
                      Recent Queries
                    </h3>
                    {history.queries.length > 0 ? (
                      <div className="space-y-3">
                        {history.queries.slice(0, 10).map((query, index) => (
                          <div key={query._id} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <p className="text-gray-900 font-medium mb-2">{query.query}</p>
                                <p className="text-sm text-gray-500">
                                  <i className="fas fa-calendar mr-1"></i>
                                  {new Date(query.timestamp).toLocaleString()}
                                </p>
                              </div>
                              <button
                                onClick={() => {
                                  setQuery(query.query);
                                  setActiveTab('query');
                                }}
                                className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                              >
                                <i className="fas fa-redo mr-1"></i>
                                Re-run
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <i className="fas fa-search text-3xl mb-4"></i>
                        <p>No queries found. Start by submitting your first legal query!</p>
                      </div>
                    )}
                  </div>

                  {/* Recent Results */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      <i className="fas fa-file-alt mr-2 text-gray-600"></i>
                      Recent Analysis Results
                    </h3>
                    {history.results.length > 0 ? (
                      <div className="space-y-3">
                        {history.results.slice(0, 10).map((result, index) => (
                          <div key={result._id} className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                            <div className="flex justify-between items-start mb-3">
                              <div className="flex-1">
                                <h4 className="font-medium text-gray-900 mb-2">
                                  {result.summary ? result.summary.substring(0, 100) + '...' : 'Analysis Result'}
                                </h4>
                                <div className="flex items-center space-x-4 text-sm text-gray-500">
                                  <span>
                                    <i className="fas fa-calendar mr-1"></i>
                                    {new Date(result.timestamp).toLocaleString()}
                                  </span>
                                  <span>
                                    <i className="fas fa-file-alt mr-1"></i>
                                    {result.case_count} cases
                                  </span>
                                  <span>
                                    <i className="fas fa-gavel mr-1"></i>
                                    {result.issues_count} issues
                                  </span>
                                  <span>
                                    <i className="fas fa-quote-left mr-1"></i>
                                    {result.citations_count} citations
                                  </span>
                                </div>
                              </div>
                              <div className="flex items-center space-x-2">
                                <div className="text-right">
                                  <div className="text-sm font-medium text-gray-700">
                                    {Math.round((result.confidence || 0) * 100)}% confidence
                                  </div>
                                  <div className="w-16 bg-gray-200 rounded-full h-2 mt-1">
                                    <div
                                      className="bg-primary-600 h-2 rounded-full"
                                      style={{ width: `${(result.confidence || 0) * 100}%` }}
                                    ></div>
                                  </div>
                                </div>
                              </div>
                            </div>
                            <div className="flex justify-end">
                              <button
                                onClick={() => {
                                  setResults(result.result);
                                  setActiveTab('query');
                                }}
                                className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                              >
                                <i className="fas fa-eye mr-1"></i>
                                View Details
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <i className="fas fa-file-alt text-3xl mb-4"></i>
                        <p>No analysis results found. Submit a query to see results here!</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <i className="fas fa-exclamation-triangle text-3xl mb-4"></i>
                  <p>Failed to load history. Please try refreshing.</p>
                </div>
              )}
            </div>
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
