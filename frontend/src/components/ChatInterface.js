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
    if (isAuthenticated) {
      fetchHistory();
    }
  }, [isAuthenticated]);

  const fetchHistory = async () => {
    if (!isAuthenticated) return;
    
    setHistoryLoading(true);
    try {
      const response = await apiClient.get('/api/user/history');
      setHistory(response.data.queries || []);
    } catch (err) {
      console.error('Error fetching history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* History Sidebar */}
      <aside className={`lg:col-span-1 ${sidebarOpen ? 'block' : 'hidden lg:block'} flex flex-col`}>
        <div className="card sticky top-4 flex-1 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">History</h3>
            <div className="flex items-center gap-2">
              <button 
                onClick={fetchHistory}
                disabled={historyLoading}
                className="text-sm text-gray-600 hover:text-gray-800"
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
          
          {historyLoading ? (
            <div className="text-center py-4">
              <i className="fas fa-spinner fa-spin text-gray-400 mb-2"></i>
              <p className="text-sm text-gray-600">Loading history...</p>
            </div>
          ) : history.length > 0 ? (
            <div className="space-y-2 flex-1 overflow-y-auto">
              {history.slice(0, 10).map((item, index) => (
                <div 
                  key={item._id || index}
                  onClick={async () => {
                    setQuery(item.query);
                    setMode('query');
                    // Fetch results from MongoDB instead of re-running query
                    try {
                      const response = await apiClient.get(`/api/user/history/${item._id}`);
                      if (response.data && response.data.result) {
                        // Display the stored results
                        setResults(response.data.result);
                        setError(null);
                      }
                    } catch (err) {
                      console.error('Error fetching history results:', err);
                      setError('Failed to load previous results');
                    }
                  }}
                  className="p-3 bg-gray-50 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors"
                >
                  <p className="text-sm text-gray-900 font-medium line-clamp-2">{item.query}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(item.timestamp).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-600">No queries yet. Start by asking a question!</p>
          )}
        </div>
      </aside>

      <section className="lg:col-span-3 space-y-6">
        {/* Mobile sidebar toggle */}
        <div className="lg:hidden mb-4">
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="btn-secondary"
          >
            <i className="fas fa-history mr-2"></i>
            {sidebarOpen ? 'Hide' : 'Show'} History
          </button>
        </div>

        {/* User Details - Bottom Left Corner */}
        {isAuthenticated && user && (
          <div className="fixed bottom-4 left-4 bg-white rounded-lg shadow-lg p-3 border border-gray-200 z-10">
            <div className="flex items-center gap-2">
              {user.picture && (
                <img 
                  src={user.picture} 
                  alt="User avatar" 
                  className="w-8 h-8 rounded-full object-cover"
                />
              )}
              <div>
                <p className="text-sm font-medium text-gray-900">{user.name}</p>
                <p className="text-xs text-gray-500">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        <div className="card">
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
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
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
      </section>
    </div>
  );
};

export default ChatInterface;


