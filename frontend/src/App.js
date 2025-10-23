import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './index.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import NavBar from './components/NavBar';
import HomePage from './components/HomePage';
import ChatInterface from './components/ChatInterface';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiUrl, setApiUrl] = useState(process.env.REACT_APP_API_URL || 'http://localhost:8000');
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
      // Check auth status and redirect to /app
      checkAuthStatus().then(() => {
        // Redirect to /app after successful authentication
        window.location.href = '/app';
      });
    } else {
      checkAuthStatus();
    }
  }, [apiUrl]);

  // History fetching is now handled in ChatInterface component

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
  return (
    <Router>
      <div className="min-h-screen bg-white flex flex-col">
        <NavBar onLogin={handleGoogleLogin} onLogout={handleLogout} isAuthenticated={isAuthenticated} user={user} />
        <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<HomePage user={user} isAuthenticated={isAuthenticated} />} />
            <Route path="/pricing" element={<HomePage user={user} isAuthenticated={isAuthenticated} />} />
            <Route path="/app" element={
              <ChatInterface
                apiClient={apiClient}
                isAuthenticated={isAuthenticated}
                user={user}
                onSubmitQuery={handleSubmit}
                onPDFComplete={handlePDFAnalysisComplete}
                results={results}
                error={error}
                loading={loading}
                query={query}
                setQuery={setQuery}
                setResults={setResults}
                setError={setError}
              />
            } />
          </Routes>
        </main>
        <footer className="bg-white border-t border-gray-200 mt-auto">
          <div className="w-full px-4 sm:px-6 lg:px-8 py-6">
            <div className="text-center text-gray-600">
              <p>&copy; 2024 VeritasAI Legal Multi-Agent System. Built with React & Tailwind CSS.</p>
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
