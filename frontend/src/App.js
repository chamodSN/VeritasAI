// src/App.js
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext } from './context/AuthContext'; 
import LandingPage from './pages/LandingPage';
import AppPage from './pages/AppPage';
import AuthCallback from './pages/AuthCallback';
import { apiClient } from './lib/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  const checkAuth = async () => {
    const token = localStorage.getItem('veritasai_token');
    if (!token) { setAuthLoading(false); return; }
    try {
      const res = await apiClient.get('/api/auth/me');
      setUser(res.data);
    } catch {
      localStorage.removeItem('veritasai_token');
    } finally {
      setAuthLoading(false);
    }
  };

  const login = () => {
    window.location.href = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/auth/google`;
  };

  const logout = async () => {
    try { await apiClient.post('/api/auth/logout'); } catch {}
    localStorage.removeItem('veritasai_token');
    setUser(null);
  };

  useEffect(() => { checkAuth(); }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-parchment flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <ScalesIcon className="w-10 h-10 text-sage animate-pulse" />
          <p className="text-sm text-mist font-sans">Loading VeritasAI…</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, checkAuth }}>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route
            path="/app"
            element={user ? <AppPage /> : <Navigate to="/" replace />}
          />
        </Routes>
      </Router>
    </AuthContext.Provider>
  );
}

function ScalesIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 3v18M5 8l7-5 7 5M5 8l3 7H2l3-7zM19 8l3 7h-6l3-7zM3 21h18" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}