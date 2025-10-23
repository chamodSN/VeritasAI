import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ResultSection from './ResultSection';
import CitationsSection from './CitationsSection';
import PDFUpload from './PDFUpload';
import ExportActions from './ExportActions';

const ChatInterface = ({ apiClient, isAuthenticated, user, onSubmitQuery, onPDFComplete, results, error, loading, query, setQuery, setResults, setError }) => {
  const [mode, setMode] = useState('query');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const resultRef = useRef(null);

  // Fetch history when authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      fetchHistory();
    }
  }, [isAuthenticated, user]);


  const fetchHistory = async () => {
    if (!isAuthenticated || !user) return;
    
    setHistoryLoading(true);
    try {
      console.log('Fetching history for user:', user.user_id);
      const response = await apiClient.get('/api/user/history');
      console.log('History response:', response.data);
      setHistory(response.data.queries || []);
    } catch (err) {
      console.error('Error fetching history:', err);
      if (err.response?.status === 401) {
        setError('Authentication expired. Please log in again.');
      } else {
        setError('Failed to load history');
      }
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="w-full min-h-screen flex">
      {/* History Sidebar - Fixed Left */}
      <aside className={`w-80 ${sidebarOpen ? 'block' : 'hidden lg:block'} flex flex-col bg-gray-50 border-r border-gray-200`}>
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">History</h3>
            <div className="flex items-center gap-2">
              <button 
                onClick={fetchHistory}
                disabled={historyLoading}
                className="text-sm text-gray-600 hover:text-gray-800 p-1 rounded hover:bg-gray-100"
                title="Refresh history"
              >
                {historyLoading ? (
                  <i className="fas fa-spinner fa-spin"></i>
                ) : (
                  <i className="fas fa-refresh"></i>
                )}
              </button>
              <button 
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden text-sm text-gray-600 hover:text-gray-800"
              >
                <i className="fas fa-chevron-left"></i>
              </button>
            </div>
          </div>
          
          {/* User Info aligned with history */}
          {isAuthenticated && user && (
            <div className="flex items-center gap-3 mb-4 p-3 bg-white rounded-lg border border-gray-200">
              {user.picture && (
                <img 
                  src={user.picture} 
                  alt="User avatar" 
                  className="w-10 h-10 rounded-full object-cover"
                />
              )}
              <div>
                <p className="text-sm font-medium text-gray-900">{user.name}</p>
                <p className="text-xs text-gray-500">{user.email}</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          {historyLoading ? (
            <div className="text-center py-4">
              <i className="fas fa-spinner fa-spin text-gray-400 mb-2"></i>
              <p className="text-sm text-gray-600">Loading history...</p>
            </div>
          ) : history.length > 0 ? (
            <div className="space-y-2">
              {history
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                .slice(0, 10)
                .map((item, index) => (
                <div 
                  key={item._id || index}
                  onClick={async () => {
                    setQuery(item.query);
                    setMode('query');
                    setError(null);
                    
                    // Try to fetch results for this query
                    try {
                      console.log('Searching for query:', item.query);
                      const response = await apiClient.get(`/api/user/results/by-query?query=${encodeURIComponent(item.query)}&timestamp=${encodeURIComponent(item.timestamp)}`);
                      console.log('Results response:', response.data);
                      if (response.data && response.data.result && !response.data.error) {
                        setResults(response.data.result);
                      } else {
                        setResults(null);
                        setError('No previous results found for this query');
                      }
                    } catch (err) {
                      console.error('Error fetching history results:', err);
                      setResults(null);
                      setError('Failed to load previous results');
                    }
                  }}
                  className="p-3 bg-white hover:bg-gray-100 rounded-lg cursor-pointer transition-colors border border-gray-200"
                >
                  <p className="text-sm text-gray-900 font-medium line-clamp-2">{item.query}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(item.timestamp).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4">
              <i className="fas fa-history text-gray-400 mb-2 text-2xl"></i>
              <p className="text-sm text-gray-600">No queries yet.</p>
              <p className="text-xs text-gray-500 mt-1">Start by asking a question!</p>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {/* Mobile sidebar toggle */}
        <div className="lg:hidden p-4 border-b border-gray-200">
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="btn-secondary"
          >
            <i className="fas fa-history mr-2"></i>
            {sidebarOpen ? 'Hide' : 'Show'} History
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 p-6">
          <div className="max-w-6xl mx-auto">
            <div className="card mb-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {user?.picture && (
                    <img 
                      src={user.picture} 
                      alt="User avatar" 
                      className="w-10 h-10 rounded-full object-cover"
                    />
                  )}
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">
                      {user && user.name ? `Hi ${user.name}, welcome 👋` : 'Welcome'}
                    </h2>
                    <p className="text-sm text-gray-600">Ask a question or analyze a PDF.</p>
                  </div>
                </div>
                <div className="flex items-center bg-gray-100 rounded-full p-1">
                  <button onClick={() => setMode('query')} className={`px-3 py-1 text-sm rounded-full ${mode === 'query' ? 'bg-white shadow font-medium' : ''}`}>Query</button>
                  <button onClick={() => setMode('pdf')} className={`px-3 py-1 text-sm rounded-full ${mode === 'pdf' ? 'bg-white shadow font-medium' : ''}`}>PDF</button>
                </div>
              </div>

              <AnimatePresence mode="wait">
                {mode === 'query' ? (
                  <motion.form key="query-mode" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} onSubmit={onSubmitQuery} className="space-y-4">
                    <textarea
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Enter your legal query..."
                      className="input-field"
                      rows="3"
                      disabled={loading || !isAuthenticated}
                    />
                    <div className="flex gap-2">
                      <button type="submit" disabled={loading || !query.trim() || !isAuthenticated} className="btn-primary">
                        {loading ? (<><i className="fas fa-spinner fa-spin mr-2"></i>Processing...</>) : (<><i className="fas fa-paper-plane mr-2"></i>Submit</>)}
                      </button>
                      <button type="button" onClick={() => setQuery('')} className="btn-secondary">
                        <i className="fas fa-times mr-2"></i>Clear
                      </button>
                    </div>
                  </motion.form>
                ) : (
                  <motion.div key="pdf-mode" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                    <PDFUpload apiClient={apiClient} isAuthenticated={isAuthenticated} onAnalysisComplete={onPDFComplete} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>


            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <div className="flex">
                  <i className="fas fa-exclamation-triangle text-red-400 mt-1 mr-3"></i>
                  <div>
                    <h3 className="text-sm font-medium text-red-800">Error</h3>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {results && (
              <div className="space-y-6" ref={resultRef}>
                <ResultSection title="Summary" icon="fa-file-alt" iconColor="text-green-600" content={results.summary} />
                <ResultSection title="Legal Issues Identified" icon="fa-gavel" iconColor="text-blue-600" content={results.issues} />
                <ResultSection title="Legal Arguments" icon="fa-comments" iconColor="text-purple-600" content={results.arguments} />
                <CitationsSection content={results.citations} />
                <ResultSection title="Analytics & Patterns" icon="fa-chart-line" iconColor="text-teal-600" content={results.analytics} />

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div className="flex items-start">
                    <i className="fas fa-info-circle text-yellow-500 mr-2 mt-0.5" />
                    <p className="text-sm text-yellow-800">This is an AI-generated analysis and may contain inaccuracies. Please verify facts before reliance.</p>
                  </div>
                </div>
                <ExportActions targetRef={resultRef} plainText={JSON.stringify(results, null, 2)} />
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default ChatInterface;